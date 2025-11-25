# backend/services/stock_service.py
import yfinance as yf
import pandas as pd
import numpy as np

class StockService:
    def __init__(self):
        pass

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