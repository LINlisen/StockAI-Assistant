# backend/services/stock_service.py
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor

class StockService:
    # 預定義一份掃描清單 (這裡以台灣50成分股為例，可自行擴充)
    TW50_TICKERS = [
        "2330", "2317", "2454", "2308", "2303", "2881", "2882", "2382", "2891", "2886",
        "2412", "2884", "2885", "1216", "2892", "2357", "2002", "2880", "2883", "2887",
        "3008", "1101", "2890", "2345", "5880", "2395", "2327", "3045", "5871", "3034",
        "3711", "2801", "6669", "6505", "2379", "3037", "2912", "5876", "1303", "1301",
        "1326", "4904", "2603", "9910", "1590", "2317", "3017"
    ]

    FINANCE_TICKERS = [
        "2881", "2882", "2891", "2886", "2884", "2885", "2892", "2880", "2883", "2887", # 金控
        "2890", "5880", "2888", "2889", "2838", "2834", "2801", "2812", "2809", "2845", # 銀行
        "5876", "6005" # 證券
    ]

    def __init__(self):
        pass

    def fetch_data_batch(self, tickers: list) -> dict:
        """
        批次下載股票資料 (使用多執行緒加速)
        """
        data_map = {}
        
        def download_one(stock_id):
            try:
                # 判斷上市或上櫃
                ticker = f"{stock_id}.TW"
                df = yf.Ticker(ticker).history(period="6mo")
                if df.empty:
                    ticker = f"{stock_id}.TWO"
                    df = yf.Ticker(ticker).history(period="6mo")
                
                if not df.empty:
                    data_map[stock_id] = df
            except Exception:
                pass

        # 開 10 條執行緒同時下載
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(download_one, tickers)
            
        return data_map
    
    def check_strategies(self, df: pd.DataFrame, strategies: list) -> list:
        """
        檢查單一股票是否符合策略，回傳符合的策略名稱列表
        """
        if len(df) < 120: return [] # 資料太少不跑
        
        matched = []
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        # --- 計算基礎指標 ---
        # 均線
        ma5 = df['Close'].rolling(5).mean()
        ma20 = df['Close'].rolling(20).mean()
        ma60 = df['Close'].rolling(60).mean()   # 季線
        ma120 = df['Close'].rolling(120).mean() # 半年線
        
        # KD
        low_9 = df['Low'].rolling(9).min()
        high_9 = df['High'].rolling(9).max()
        rsv = (df['Close'] - low_9) / (high_9 - low_9) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()

        # 成交量均量
        vol_ma5 = df['Volume'].rolling(5).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # --- 策略邏輯判斷 ---

        # 1. 策略: MA20 黃金交叉 季線(MA60) 且 站上半年線(MA120) (你原本的需求)
        if "MA_Cross_Major" in strategies:
            # 條件：今天 MA20 > MA60 且 昨天 MA20 < MA60 (剛交叉) 且 收盤價 > MA120
            cond_cross = (ma20.iloc[-1] > ma60.iloc[-1]) and (ma20.iloc[-2] <= ma60.iloc[-2])
            cond_above_half = curr['Close'] > ma120.iloc[-1]
            if cond_cross and cond_above_half:
                matched.append("MA20穿過季線且站穩半年線")

        # 2. 策略: KD 黃金交叉
        if "KD_Golden_Cross" in strategies:
            # K 向上突破 D，且 D < 50 (低檔金叉比較準)
            if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2] and d.iloc[-1] < 50:
                matched.append("KD低檔黃金交叉")

        # 3. 策略: 爆量長紅
        if "Volume_Explosion" in strategies:
            # 成交量 > 5日均量 * 2 且 漲幅 > 3%
            is_explode = curr['Volume'] > (vol_ma5.iloc[-2] * 2)
            is_up = (curr['Close'] - prev['Close']) / prev['Close'] > 0.03
            if is_explode and is_up:
                matched.append("爆量長紅")

        # 4. 策略: RSI 超賣反彈
        if "RSI_Oversold" in strategies:
            # RSI < 30
            if rsi.iloc[-1] < 30:
                matched.append("RSI超賣(<30)")

        # 5. 策略: 均線多頭排列
        if "Bullish_Alignment" in strategies:
            # MA5 > MA20 > MA60
            if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
                matched.append("均線多頭排列")

        return matched

    def fetch_data(self, stock_id: str) -> pd.DataFrame:
        """
        抓取股票數據，自動判斷上市(.TW)或上櫃(.TWO)
        """
        ticker = f"{stock_id}.TW"
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")

        if df.empty:
            ticker = f"{stock_id}.TWO"
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
        
        if df.empty:
            raise ValueError(f"無法獲取股票 {stock_id} 的數據")
            
        return df
    
    def screen_stocks(self, strategies: list, scope: str = "TW50", custom_list: list = None) -> list:
        """
        執行選股主程式
        :param strategies: 策略列表
        :param scope: 掃描範圍 (TW50, Finance, Custom)
        :param custom_list: 自訂股票代號列表 (當 scope=Custom 時使用)
        """
        
        # 1. 決定要掃描的股票清單
        target_tickers = []
        
        if scope == "Custom":
            if custom_list:
                target_tickers = custom_list
            else:
                return [] # 沒給清單就回傳空
        elif scope == "Finance":
            target_tickers = self.FINANCE_TICKERS
        else:
            # 預設為 TW50
            target_tickers = self.TW50_TICKERS

        stock_data = self.fetch_data_batch(target_tickers)
        
        results = []
        
        # 2. 逐一檢查
        for stock_id, df in stock_data.items():
            matched_strats = self.check_strategies(df, strategies)
            
            if matched_strats:
                results.append({
                    "stock_id": stock_id,
                    "name": stock_id, # 暫時用代號當名稱
                    "close": float(df.iloc[-1]['Close']),
                    "matched_strategies": matched_strats
                })
        
        return results

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        移植原本的指標計算邏輯
        """
        # 避免修改原始 DataFrame，建立副本
        data = df.copy()

        # 1. 移動平均線 (MA)
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA60'] = data['Close'].rolling(window=60).mean()

        # 2. 布林通道 (Bollinger Bands)
        std20 = data['Close'].rolling(window=20).std()
        data['Upper'] = data['MA20'] + (std20 * 2)
        data['Lower'] = data['MA20'] - (std20 * 2)

        # 3. KD 指標
        low_9 = data['Low'].rolling(window=9).min()
        high_9 = data['High'].rolling(window=9).max()
        rsv = (data['Close'] - low_9) / (high_9 - low_9) * 100
        data['K'] = rsv.ewm(com=2).mean()
        data['D'] = data['K'].ewm(com=2).mean()

        # 4. MACD
        exp12 = data['Close'].ewm(span=12, adjust=False).mean()
        exp26 = data['Close'].ewm(span=26, adjust=False).mean()
        data['MACD'] = exp12 - exp26
        data['Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()

        # 5. OBV (能量潮)
        # diff() 計算今日與昨日差價，>0 為 1, <0 為 -1, =0 為 0
        direction = data['Close'].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        data['OBV'] = (direction * data['Volume']).fillna(0).cumsum()
        data['OBV_MA'] = data['OBV'].rolling(window=20).mean()

        # 填補 NaN (避免 JSON 序列化錯誤)
        data.fillna(0, inplace=True)
        
        return data

    def get_technical_summary(self, df: pd.DataFrame) -> dict:
        """
        取得最後一天的技術指標摘要，準備餵給 AI
        """
        curr = df.iloc[-1]
        close = curr['Close']
        
        # 簡易趨勢判斷
        trend = "多頭" if close > curr['MA60'] else "空頭"
        obv_signal = "吸籌" if curr['OBV'] > curr['OBV_MA'] else "調節"

        # 組合成文字摘要 (Prompt Context)
        context_str = f"""
        現價: {close:.2f}, MA20: {curr['MA20']:.2f}, MA60: {curr['MA60']:.2f}
        布林上軌: {curr['Upper']:.2f}, 下軌: {curr['Lower']:.2f}
        KD指標: K={curr['K']:.2f}, D={curr['D']:.2f}
        MACD: {curr['MACD']:.2f}
        OBV趨勢: {obv_signal}
        """
        
        return {
            "close": close,
            "trend": trend,
            "obv_signal": obv_signal,
            "context_str": context_str,
            "last_row_dict": curr.to_dict() # 保留完整數據備用
        }