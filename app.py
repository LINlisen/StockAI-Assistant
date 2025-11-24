import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import io
import os

# 嘗試匯入 Google Generative AI
try:
    import google.generativeai as genai
except ImportError:
    st.error("請先安裝 google-generativeai 套件")
    genai = None

# --- 設定網頁標題與排版 ---
st.set_page_config(page_title="台股 AI 操盤分析師", layout="wide")
st.title("📈 台股 AI 操盤分析師 (Gemini 驅動)")

# --- 側邊欄輸入區 ---
with st.sidebar:
    st.header("⚙️ 設定參數")
    api_key_input = st.text_input("輸入 Gemini API Key", type="password", help="請輸入您的 Google AI Studio API Key")
    stock_id = st.text_input("股票代號 (例 2330)", value="2330")
    mode_sel = st.selectbox("操作方向", ["做多 (Long)", "做空 (Short)"])
    cost_input = st.number_input("持倉成本 (空手請填 0)", min_value=0.0, value=0.0)
    run_btn = st.button("🚀 開始分析", type="primary")

class StockAI_Gemini_Streamlit:
    def __init__(self, ticker, api_key=None):
        self.ticker_raw = ticker
        self.ticker = f"{ticker}.TW"
        self.df = None
        self.api_key = api_key
        self.model = None
        
        if api_key and genai:
            try:
                genai.configure(api_key=api_key)
                self.model = self.find_best_model()
            except Exception as e:
                st.error(f"Gemini 初始化失敗: {e}")

    def find_best_model(self):
        """ 自動列出帳號可用模型，並選擇最佳的一個 """
        print("🔍 正在偵測您的 API 可用模型...")
        try:
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            # 優先順序: 1.5-flash (快) -> 1.5-pro (強) -> 1.0-pro (穩) -> 隨便一個
            target_model = None
            for m in available_models:
                if "gemini-1.5-flash" in m:
                    target_model = m
                    break
            
            if not target_model:
                for m in available_models:
                    if "gemini-1.5-pro" in m:
                        target_model = m
                        break
            
            if not target_model:
                for m in available_models:
                    if "gemini-pro" in m:
                        target_model = m
                        break
            
            # 如果都沒對應到，就選列表中的第一個
            if not target_model and available_models:
                target_model = available_models[0]
                
            if target_model:
                print(f"✅ 已自動選定模型: {target_model}")
                return genai.GenerativeModel(target_model)
            else:
                print("⚠️ 找不到任何支援 generateContent 的模型，請檢查 API Key 權限。")
                return None
                
        except Exception as e:
            print(f"無法列出模型 (可能是 API Key 無效或網路問題): {e}")
            return None
        
    def fetch_data(self):
        with st.spinner(f"正在抓取 {self.ticker_raw} 數據..."):
            try:
                stock = yf.Ticker(self.ticker)
                self.df = stock.history(period="1y")
                if self.df.empty:
                    self.ticker = f"{self.ticker_raw}.TWO"
                    stock = yf.Ticker(self.ticker)
                    self.df = stock.history(period="1y")
                return not self.df.empty
            except Exception as e:
                st.error(f"數據錯誤: {e}")
                return False

    def calculate_indicators(self):
        self.df['MA20'] = self.df['Close'].rolling(window=20).mean()
        self.df['MA60'] = self.df['Close'].rolling(window=60).mean()
        
        std20 = self.df['Close'].rolling(window=20).std()
        self.df['Upper'] = self.df['MA20'] + (std20 * 2)
        self.df['Lower'] = self.df['MA20'] - (std20 * 2)
        
        low_9 = self.df['Low'].rolling(window=9).min()
        high_9 = self.df['High'].rolling(window=9).max()
        rsv = (self.df['Close'] - low_9) / (high_9 - low_9) * 100
        self.df['K'] = rsv.ewm(com=2).mean()
        self.df['D'] = self.df['K'].ewm(com=2).mean()
        
        exp12 = self.df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = self.df['Close'].ewm(span=26, adjust=False).mean()
        self.df['MACD'] = exp12 - exp26
        self.df['Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        
        self.df['OBV'] = (self.df['Close'].diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0)) * self.df['Volume']).fillna(0).cumsum()
        self.df['OBV_MA'] = self.df['OBV'].rolling(window=20).mean()

    def ask_gemini(self, context_data, user_mode, user_cost):
        if not self.model:
            return "⚠️ 請在左側輸入正確的 API Key 以啟用 AI 分析。"

        with st.spinner("🤖 AI 正在撰寫分析報告..."):
            prompt = f"""
            你是一位資深台股操盤手。請分析以下股票數據。
            參數: 代號 {self.ticker_raw}, 方向 {user_mode}, 成本 {user_cost}
            數據: {context_data}
            
            任務:
            1. 給出明確操作建議 (買進/賣出/續抱/止損)。
            2. 指出關鍵支撐與壓力價位。
            3. 使用條列式，口語化，400字內。
            4. 給出明確的價位操作，是否適合作為隔日沖的標的。
            """
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Gemini 回應錯誤: {e}"

    def run_analysis(self, mode, cost):
        curr = self.df.iloc[-1]
        close = curr['Close']
        trend = "多頭" if close > curr['MA60'] else "空頭"
        obv_signal = "吸籌" if curr['OBV'] > curr['OBV_MA'] else "調節"
        
        # 顯示關鍵數據指標
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("現價", f"{close:.2f}")
        col2.metric("趨勢", trend)
        col3.metric("籌碼狀態", obv_signal)
        col4.metric("KD指標", f"K{curr['K']:.1f} / D{curr['D']:.1f}")

        technical_context = f"""
        現價: {close:.2f}, MA20: {curr['MA20']:.2f}, MA60: {curr['MA60']:.2f}
        布林上軌: {curr['Upper']:.2f}, 下軌: {curr['Lower']:.2f}
        KD: K={curr['K']:.2f}, D={curr['D']:.2f}
        MACD: {curr['MACD']:.2f}
        OBV趨勢: {obv_signal}
        """
        
        ai_res = self.ask_gemini(technical_context, mode, cost)
        
        st.subheader("🧠 Gemini AI 分析報告")
        st.info(ai_res)

    def plot_chart(self):
        mc = mpf.make_marketcolors(up='r', down='g', inherit=True)
        s = mpf.make_mpf_style(marketcolors=mc, rc={'font.size': 10})
        
        apds = [
            mpf.make_addplot(self.df['Upper'], color='gray', linestyle='--', width=0.8),
            mpf.make_addplot(self.df['Lower'], color='gray', linestyle='--', width=0.8),
            mpf.make_addplot(self.df['MA20'], color='orange', width=1.5),
            mpf.make_addplot(self.df['K'], panel=2, color='fuchsia', ylabel='KD'),
            mpf.make_addplot(self.df['D'], panel=2, color='b'),
            mpf.make_addplot(self.df['OBV'], panel=3, color='purple', ylabel='OBV', width=1.5),
        ]

        # 關鍵：將圖表存入 Buffer 而不是直接顯示視窗
        buf = io.BytesIO()
        mpf.plot(
            self.df, type='candle', volume=True, addplot=apds,
            title=f"\n{self.ticker_raw} Technical Chart",
            style=s, panel_ratios=(5,1,2,2), figratio=(12, 10), tight_layout=True,
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )
        st.image(buf, use_container_width=True)

# --- 主程式邏輯 ---
if run_btn:
    if not stock_id:
        st.warning("請輸入股票代號")
    else:
        app = StockAI_Gemini_Streamlit(stock_id, api_key=api_key_input)
        if app.fetch_data():
            app.calculate_indicators()
            app.run_analysis(mode_sel, cost_input)
            app.plot_chart()
        else:
            st.error("❌ 找不到股票代號或資料下載失敗")
