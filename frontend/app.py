# frontend/app.py
import streamlit as st
import requests
import pandas as pd
import mplfinance as mpf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from stock_mapping import get_stock_name, get_stock_symbol
from streamlit_cookies_manager import EncryptedCookieManager
import re
import json

# 使用 try-except 包起來
try:
    # 嘗試讀取 secrets，如果沒有檔案會報錯，就會跳到 except
    if "BACKEND_URL" in st.secrets:
        BACKEND_URL = st.secrets["BACKEND_URL"]
    else:
        BACKEND_URL = "http://127.0.0.1:8000"
except FileNotFoundError:
    # 如果本地沒有 secrets.toml 檔案，就預設使用 localhost
    BACKEND_URL = "http://127.0.0.1:8000"
except Exception:
    # 捕捉其他可能的 secrets 錯誤
    BACKEND_URL = "http://127.0.0.1:8000"

# 初始化 Cookie Manager
cookies = EncryptedCookieManager(
    prefix="stockai_",
    password="stockai-secret-key-2024-change-in-production"
)

if not cookies.ready():
    st.stop()

def create_interactive_candlestick_chart(df, stock_id, chart_style, drawing_color="#BB86FC", key_levels=None, show_ma=None, show_bb=True, show_vol=True):
    """
    建立互動式 K 線圖，包含：
    - Hover 顯示完整價格資訊
    - 5MA, 10MA, 20MA, 60MA 均線
    - 成交量子圖
    - 繪圖工具 (垂直線、矩形框)
    
    參數:
        df: 股票資料 DataFrame
        stock_id: 股票代號
        chart_style: 圖表配色方案
        drawing_color: 畫線顏色 (預設亮紫色)
        key_levels: 關鍵價位
        show_ma: 要顯示的均線列表
        show_bb: 是否顯示布林通道
        show_vol: 是否顯示成交量
    """
    if show_ma is None:
        show_ma = ['MA5', 'MA10', 'MA20', 'MA60']

    # 計算均線（只計算需要的）
    for ma in show_ma:
        if ma == 'MA5' and 'MA5' not in df.columns:
            df['MA5'] = df['Close'].rolling(window=5).mean()
        elif ma == 'MA10' and 'MA10' not in df.columns:
            df['MA10'] = df['Close'].rolling(window=10).mean()
        elif ma == 'MA20' and 'MA20' not in df.columns:
            df['MA20'] = df['Close'].rolling(window=20).mean()
        elif ma == 'MA60' and 'MA60' not in df.columns:
            df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # 建立子圖：主圖 (K線+均線) + 副圖 (成交量)
    has_volume = 'Volume' in df.columns and show_vol
    
    if has_volume:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
            subplot_titles=(f'{stock_id} K線圖', '成交量')
        )
    else:
        fig = make_subplots(
            rows=1, cols=1,
            subplot_titles=(f'{stock_id} K線圖',)
        )
    
    # 設定配色方案
    if "紅綠" in chart_style:
        # 台灣習慣：漲紅跌綠
        increasing_color = '#FF0000'  # 紅色
        decreasing_color = '#00FF00'  # 綠色
    else:
        # 黑白配色：漲白跌黑
        increasing_color = '#FFFFFF'  # 白色
        decreasing_color = '#000000'  # 黑色
    
    # 加入 K 線圖
    candlestick = go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='K線',
        increasing_line_color=increasing_color,
        decreasing_line_color=decreasing_color,
        hovertemplate='<b>日期</b>: %{x|%Y-%m-%d}<br>' +
                      '<b>開盤</b>: %{open:.2f}<br>' +
                      '<b>最高</b>: %{high:.2f}<br>' +
                      '<b>最低</b>: %{low:.2f}<br>' +
                      '<b>收盤</b>: %{close:.2f}<br>' +
                      '<extra></extra>'
    )
    fig.add_trace(candlestick, row=1, col=1)
    
    # 加入均線
    ma_colors = {
        'MA5': '#FF6B6B',   # 淺紅
        'MA10': '#4ECDC4',  # 青色
        'MA20': '#FFD93D',  # 黃色
        'MA60': '#95E1D3'   # 淺綠
    }
    
    # 中文均線名稱對應
    ma_names_zh = {
        'MA5': '5日均線',
        'MA10': '10日均線',
        'MA20': '20日均線',
        'MA60': '60日均線'
    }
    
    for ma_name, color in ma_colors.items():
        if ma_name in df.columns and ma_name in show_ma:  # 只繪製存在的均線
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[ma_name],
                    name=ma_names_zh[ma_name],
                    line=dict(color=color, width=1.5),
                    hovertemplate=f'<b>{ma_names_zh[ma_name]}</b>: %{{y:.2f}}<extra></extra>'
                ),
                row=1, col=1
            )

    # 加入布林通道 (如果有資料)
    if show_bb and 'Upper' in df.columns and 'Lower' in df.columns:
        # 上軌
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Upper'],
                name='布林上軌',
                line=dict(color='rgba(128, 128, 128, 0.5)', width=1, dash='dash'), # 灰色虛線
                hovertemplate='<b>上軌</b>: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        # 下軌 (填滿與上軌之間的區域)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['Lower'],
                name='布林下軌',
                line=dict(color='rgba(128, 128, 128, 0.5)', width=1, dash='dash'),
                fill='tonexty', # 填滿與上一條線(上軌)之間的區域
                fillcolor='rgba(128, 128, 128, 0.05)', # 極淡灰色
                hovertemplate='<b>下軌</b>: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # 加入成交量 (如果有)
    if has_volume:
        # 根據漲跌設定成交量顏色 - 使用 reset_index 來避免迭代問題
        df_temp = df.reset_index()
        colors = []
        for idx in range(len(df_temp)):
            if df_temp.loc[idx, 'Close'] >= df_temp.loc[idx, 'Open']:
                colors.append(increasing_color)
            else:
                colors.append(decreasing_color)
        
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                name='成交量',
                marker_color=colors,
                hovertemplate='<b>成交量</b>: %{y:,.0f}<extra></extra>'
            ),
            row=2, col=1
        )
    
    if key_levels:
        # A. 畫壓力線 (Resistance) - 紅色虛線
        if key_levels.get('res'):
            fig.add_hline(
                y=key_levels['res'], 
                line_dash="dash", line_color="red", line_width=1.5,
                annotation_text=f"壓力 {key_levels['res']}", 
                annotation_position="top right",
                row=1, col=1
            )

        # B. 畫支撐線 (Support) - 綠色虛線
        if key_levels.get('sup'):
            fig.add_hline(
                y=key_levels['sup'], 
                line_dash="dash", line_color="green", line_width=1.5,
                annotation_text=f"支撐 {key_levels['sup']}", 
                annotation_position="bottom right",
                row=1, col=1
            )

        # C. 標示爆量日期 (Volume Spike)
        if key_levels.get('date'):
            try:
                spike_date = pd.to_datetime(key_levels['date'])
                # 確保日期在資料範圍內
                if spike_date in df.index:
                    # 取得當天高點，把箭頭畫在 K 棒上方
                    high_val = df.loc[spike_date]['High']
                    
                    fig.add_annotation(
                        x=spike_date, y=high_val,
                        text="爆量日", showarrow=True,
                        arrowhead=1, arrowsize=2, arrowwidth=2,
                        arrowcolor="#BB86FC", # 使用你在前端設定的亮紫色
                        ay=-40, # 箭頭向上偏移
                        row=1, col=1
                    )
            except Exception as e:
                print(f"日期標示錯誤: {e}")
    
    # 更新布局
    fig.update_layout(
        title=f'{stock_id} 技術分析圖',
        yaxis_title='價格 (TWD)',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        height=700,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        # 啟用繪圖工具
        dragmode='zoom',
        modebar=dict(
            add=['drawline', 'drawrect', 'eraseshape']
        ),
        # 設定畫線顏色
        newshape=dict(
            line_color=drawing_color,
            line_width=2,
            opacity=0.8
        )
    )
    
    # 隱藏非交易日（週末和假日）
    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"]),  # 隱藏週末
        ]
    )
    
    if has_volume:
        fig.update_yaxes(title_text="價格 (TWD)", row=1, col=1)
        fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    fig.update_xaxes(title_text="日期", row=2 if has_volume else 1, col=1)
    
    return fig



st.set_page_config(page_title="台股 AI 操盤系統", layout="wide")

# --- 初始化 Session State ---
# 先檢查 Cookie 是否有登入資訊（自動登入）
if cookies.get("user_id") and not st.session_state.get("logged_in"):
    try:
        user_id = cookies.get("user_id")
        # 從後端重新獲取使用者資料
        res = requests.get(f"{BACKEND_URL}/api/users/{user_id}")
        if res.status_code == 200:
            st.session_state.logged_in = True
            st.session_state.user_info = res.json()
    except:
        # Cookie 無效，清除
        cookies["user_id"] = ""
        cookies["logged_in"] = ""
        cookies.save()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = {}

# ==========================================
#  頁面 1: 登入 / 註冊 介面
# ==========================================
def login_page():
    st.title("🔐 歡迎使用台股 AI 操盤系統")
    
    tab1, tab2 = st.tabs(["登入", "註冊新帳號"])
    
    # --- 登入區塊 ---
    with tab1:
        st.subheader("使用者登入")
        login_account = st.text_input("帳號", key="login_acc")
        login_password = st.text_input("密碼", type="password", key="login_pass")
        
        if st.button("登入", type="primary"):
            try:
                payload = {"account": login_account, "password": login_password}
                res = requests.post(f"{BACKEND_URL}/api/login", json=payload)
                
                if res.status_code == 200:
                    user_data = res.json()
                    st.session_state.logged_in = True
                    st.session_state.user_info = user_data
                    
                    # 寫入 Cookie (持久化登入)
                    cookies["user_id"] = str(user_data["id"])
                    cookies["logged_in"] = "true"
                    cookies.save()
                    
                    st.success(f"歡迎回來，{user_data['username']}！")
                    st.rerun() # 重新整理頁面以進入主程式
                else:
                    st.error(f"登入失敗: {res.json().get('detail')}")
            except Exception as e:
                st.error(f"連線錯誤: {e}")

    # --- 註冊區塊 ---
    with tab2:
        st.subheader("建立新帳號")
        reg_username = st.text_input("使用者名稱 (暱稱)")
        reg_account = st.text_input("設定帳號")
        reg_password = st.text_input("設定密碼", type="password")
        reg_token = st.text_input("Gemini API Token (選填，可稍後再填)", type="password")
        
        if st.button("註冊"):
            if not reg_account or not reg_password or not reg_username:
                st.warning("請填寫必填欄位")
            else:
                try:
                    payload = {
                        "username": reg_username,
                        "account": reg_account,
                        "password": reg_password,
                        "api_token": reg_token if reg_token else None
                    }
                    res = requests.post(f"{BACKEND_URL}/api/register", json=payload)
                    
                    if res.status_code == 200:
                        st.success("註冊成功！請切換到「登入」頁籤進行登入。")
                    else:
                        st.error(f"註冊失敗: {res.json().get('detail')}")
                except Exception as e:
                    st.error(f"連線錯誤: {e}")

# ==========================================
#  頁面 B: 個人設定頁面 (新增功能)
# ==========================================
def settings_page():
    st.title("👤 個人資料設定")
    
    user = st.session_state.user_info
    
    with st.form("settings_form"):
        st.subheader("基本資料")
        # 預設值帶入目前 session 中的資料
        new_username = st.text_input("使用者名稱", value=user.get("username", ""))
        
        st.subheader("API 設定")
        # 這裡會顯示目前的 API Token，方便使用者確認
        current_token = user.get("api_token") or ""
        new_token = st.text_input("Gemini API Token", value=current_token, type="password", help="設定後，分析頁面將自動帶入")
        
        st.subheader("安全性")
        new_password = st.text_input("新密碼 (若不修改請留空)", type="password")
        confirm_password = st.text_input("確認新密碼", type="password")
        
        submit_btn = st.form_submit_button("💾 儲存變更")
        
    if submit_btn:
        # 驗證密碼
        if new_password and new_password != confirm_password:
            st.error("兩次密碼輸入不一致")
            return

        payload = {
            "username": new_username,
            "api_token": new_token,
            "password": new_password if new_password else None
        }
        
        try:
            user_id = user["id"]
            res = requests.put(f"{BACKEND_URL}/api/users/{user_id}", json=payload)
            
            if res.status_code == 200:
                # 重要：更新成功後，要把最新的資料寫回 session_state
                # 這樣切換回主頁面時，才會用到最新的 Token
                st.session_state.user_info = res.json()
                st.success("資料更新成功！")
            else:
                st.error(f"更新失敗: {res.text}")
        except Exception as e:
            st.error(f"連線錯誤: {e}")

# ==========================================
#  頁面 C: AI 操盤系統 (主功能)
# ==========================================
def extract_key_levels(text):
    """
    從 AI 分析文本中提取 JSON 格式的關鍵數據
    目標格式: { "resistancePrice": "39.0", "supportPrice": 34.0, "volumeSpikeDate": "2025/12/08" }
    """
    try:
        # 使用正規表達式尋找 JSON 區塊 (假設 AI 會用大括號包起來)
        # 尋找包含 resistancePrice 的最外層大括號
        match = re.search(r'\{.*"resistancePrice".*\}', text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            return {
                "res": float(data.get("resistancePrice", 0)),
                "sup": float(data.get("supportPrice", 0)),
                "date": data.get("volumeSpikeDate", None)
            }
    except Exception as e:
        print(f"JSON 提取失敗: {e}")
    
    return None


def analysis_page():
    st.title("📈 台股 AI 操盤分析師")
    
    user = st.session_state.user_info
    
    # 從 session 取出 db 存的 token (作為預設值)
    saved_token = user.get("api_token") or ""

    # --- 側邊欄設定 ---
    with st.sidebar:
        st.header("⚙️ 參數設定")
        
        # 1. 選擇 AI 提供者
        ai_provider = st.radio("AI 模型來源", ["Google Gemini (雲端)", "Ollama (本地)"])
        provider_code = "gemini" if "Gemini" in ai_provider else "ollama"
        
        # 初始化變數
        ollama_url = None
        api_key_input = None
        selected_model = "models/gemini-2.0-flash" # 預設值

        # --- 情境 A: 使用 Google Gemini ---
        if provider_code == "gemini":
            # API Key 輸入
            api_key_input = st.text_input(
                "Gemini API Key", 
                value=saved_token, 
                type="password"
            )
            
            # --- Gemini 模型列表動態獲取邏輯 (保留你原本的功能) ---
            if "model_list" not in st.session_state:
                st.session_state.model_list = ["models/gemini-2.0-flash", "models/gemini-1.5-flash"] # 預設列表

            # 更新按鈕與選單
            col_m1, col_m2 = st.columns([4, 1])
            
            # 🔄 更新按鈕
            if col_m2.button("🔄", help="更新模型列表"):
                if api_key_input:
                    try:
                        with st.spinner("更新中..."):
                            res = requests.post(f"{BACKEND_URL}/api/models", json={"api_key": api_key_input})
                            if res.status_code == 200:
                                st.session_state.model_list = res.json()
                                st.success("已更新")
                            else:
                                st.warning("更新失敗")
                    except:
                        st.warning("無法連線後端")
            
            # 模型選擇選單
            selected_model = col_m1.selectbox("選擇 AI 模型", st.session_state.model_list, index=0)

        # --- 情境 B: 使用 Ollama (本地/自建) ---
        else:
            api_key_input = "ollama_no_key" # Ollama 不需要 Key，但後端需佔位符
            
            # Ollama 模型選擇 (包含你指定的 gemma3 與 oss)
            # 你也可以開放讓使用者自己輸入
            ollama_models = ["gemma3:12b", "gpt-oss:20b", "llama3.2:latest"]
            
            selected_model = st.selectbox(
                "選擇 Ollama 模型", 
                ollama_models,
                help="請確保後端電腦已執行 `ollama pull <模型名>`"
            )
            
            # Ollama URL (支援雲端 Ngrok)
            ollama_url = st.text_input(
                "Ollama URL", 
                value="http://localhost:11434",
                help="若是雲端部署，請填入 Ngrok 網址"
            )

        st.divider()
        style_options = {
            "standard": "🧑‍💼 標準 (資深操盤手)",
            "balanced": "⚖️ 平衡型 (穩健)",
            "aggressive": "🔥 激進型 (動能交易)",
            "conservative": "🛡️ 保守型 (價值波段)"
        }

        selected_style_label = st.selectbox("分析風格", list(style_options.values()))
        prompt_style = [k for k, v in style_options.items() if v == selected_style_label][0]
        
       # --- 股票選擇 (支援雙向查詢) ---
        st.divider()
        st.subheader("📊 股票選擇")
        
        # 建立兩欄布局
        col1, col2 = st.columns(2)
        
        with col1:
            stock_id = st.text_input("股票代號", "2330", key="stock_code_input", 
                                     help="輸入股票代號，例如：2330")
            # 顯示對應的股票名稱
            stock_name = get_stock_name(stock_id)
            if stock_name:
                st.success(f"✓ {stock_name}")
            else:
                st.warning("未知股票")
        
        with col2:
            stock_name_input = st.text_input("或輸入股票名稱", "", key="stock_name_input",
                                            help="輸入股票名稱，例如：台積電")
            # 顯示對應的股票代號
            if stock_name_input:
                stock_symbol = get_stock_symbol(stock_name_input)
                if stock_symbol:
                    st.success(f"✓ {stock_symbol}")
                    # 自動更新 stock_id（需要使用 session_state）
                    st.info(f"💡 請在左側代號欄位輸入：{stock_symbol}")
                else:
                    st.warning("未找到對應股票")
        
        # 這裡建議加上英文 mapping，因為後端通常習慣判斷 "Long"/"Short"
        mode_display = st.selectbox("操作方向", ["做多 (Long)", "做空 (Short)"])
        mode = "Long" if "Long" in mode_display else "Short"
        
        cost = st.number_input("成本", 0.0)


        # 圖表配色選擇
        st.divider()
        chart_style = st.selectbox(
            "📊 圖表配色",
            ["紅綠配色 (漲紅跌綠)", "黑白配色 (漲白跌黑)"],
            help="選擇 K 線圖的配色方案"
        )
        
        # 畫線顏色選擇
        drawing_color = st.color_picker(
            "✏️ 畫線顏色",
            value="#BB86FC",  # 亮紫色
            help="選擇繪製支撐壓力線的顏色"
        )

        st.divider()
        st.write("📈 圖表顯示設定")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            show_ma_list = st.multiselect(
                "顯示均線",
                ['MA5', 'MA10', 'MA20', 'MA60'],
                default=['MA5', 'MA10', 'MA20', 'MA60']
            )
        with col_c2:
            show_bb_check = st.checkbox("顯示布林通道", value=True)
            show_vol_check = st.checkbox("顯示成交量", value=True)
        
        run_btn = st.button("🚀 開始分析", type="primary")


    

    # --- 執行按鈕邏輯 ---
    if run_btn:
        # 檢查 Gemini Key
        if provider_code == "gemini" and not api_key_input:
            st.error("請輸入 API Key")
            return
            
        with st.spinner(f"正在呼叫 {selected_model} ({provider_code}) 進行分析..."):
            try:
                payload = {
                    "user_id": user.get('id'),
                    "stock_id": stock_id,
                    "mode": mode,
                    "cost": cost,
                    "api_key": api_key_input,
                    
                    # 🔥 關鍵參數：傳送 provider, model_name, ollama_url
                    "provider": provider_code,
                    "model_name": selected_model,
                    "ollama_url": ollama_url,
                    "prompt_style": prompt_style
                }
                
                res = requests.post(f"{BACKEND_URL}/api/analyze", json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    
                    # --- 顯示結果 ---
                    col1, col2 = st.columns(2)
                    col1.metric("現價", f"{data['current_price']:.2f}")
                    col1.metric("趨勢", data['trend'])
                    
                    st.subheader(f"🧠 AI 分析報告 ({selected_model})")
                    st.info(data['ai_analysis'])
                    
                    # 🔗 Yahoo Finance 連結
                    yahoo_url = f"https://tw.stock.yahoo.com/quote/{stock_id}.TW/technical-analysis"
                    st.markdown(f"📊 [查看 Yahoo Finance 技術分析]({yahoo_url})")
                    
                    # 繪製互動式 K 線圖
                    if data.get('technical_data'):
                        try:
                            raw = data['technical_data']
                            df = pd.DataFrame(raw)
                            df['Date'] = pd.to_datetime(df['Date'])
                            df.set_index('Date', inplace=True)
                            
                            # 確保有 OHLC 資料
                            required_cols = ['Open', 'High', 'Low', 'Close']
                            missing_cols = [col for col in required_cols if col not in df.columns]
                            key_levels = extract_key_levels(data['ai_analysis'])
                            if key_levels:
                                    k1, k2, k3 = st.columns(3)
                                    k1.metric("AI 判斷壓力", key_levels['res'])
                                    k2.metric("AI 判斷支撐", key_levels['sup'])
                                    k3.metric("爆量轉折日", key_levels['date'])
                            if missing_cols:
                                st.error(f"❌ 缺少必要欄位: {missing_cols}")
                                st.write("可用欄位:", df.columns.tolist())
                            elif all(col in df.columns for col in required_cols):
                                st.subheader("📈 互動式 K 線圖")
                                st.caption("💡 提示：可使用滑鼠 hover 查看詳細資訊，點擊右上角工具列可繪製支撐壓力線")
                                
                                
                                # 使用新的互動式圖表函數
                                fig = create_interactive_candlestick_chart(df, stock_id, chart_style, drawing_color, key_levels=key_levels, show_ma=show_ma_list, show_bb=show_bb_check, show_vol=show_vol_check)
                                
                                # 使用 st.write 顯示 Plotly 圖表（比 st.plotly_chart 更穩定）
                                st.write(fig)
                            else:
                                # 如果沒有完整 OHLC 資料，顯示折線圖
                                st.subheader("📈 收盤價走勢")
                                st.line_chart(df['Close'])
                        except Exception as e:
                            st.error(f"❌ 圖表繪製錯誤: {str(e)}")
                            st.write("錯誤詳情:", type(e).__name__)
                            import traceback
                            st.code(traceback.format_exc())
                    else:
                        st.warning("⚠️ 後端未返回 technical_data")
                else:
                    st.error(f"分析失敗: {res.text}")
            except Exception as e:
                st.error(f"錯誤: {e}")

# ==========================================
#  頁面 D: 歷史紀錄頁面 (新增)
# ==========================================
def history_page():
    st.title("📜 歷史詢問紀錄")
    user = st.session_state.user_info
    
    # 呼叫後端 API 獲取資料
    try:
        res = requests.get(f"{BACKEND_URL}/api/history/{user['id']}")
        
        if res.status_code == 200:
            history_data = res.json()
            
            if not history_data:
                st.info("目前還沒有任何紀錄喔！快去分析幾支股票吧。")
                return

            # 將資料轉為 DataFrame 以便顯示表格
            df = pd.DataFrame(history_data)
            
            # 美化時間格式
            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # 顯示摘要表格
            st.dataframe(
                df[['created_at', 'stock_id', 'mode', 'current_price', 'cost_price']],
                column_config={
                    "created_at": "查詢時間",
                    "stock_id": "代號",
                    "mode": "方向",
                    "current_price": "當時股價",
                    "cost_price": "成本"
                },
                use_container_width=True,
                hide_index=True
            )
            
            st.subheader("詳細分析內容")
            # 使用 Expander 顯示詳細 AI 建議，避免畫面太亂
            for item in history_data:
                time_str = pd.to_datetime(item['created_at']).strftime('%Y-%m-%d %H:%M')
                label = f"[{time_str}] {item['stock_id']} ({item['mode']}) - ${item['current_price']}"
                
                with st.expander(label):
                    st.markdown(f"**成本:** {item['cost_price']}")
                    st.markdown("---")
                    st.markdown(item['ai_advice'])
        else:
            st.error("無法取得歷史紀錄")
            
    except Exception as e:
        st.error(f"連線錯誤: {e}")
# ==========================================
#  頁面 E: 智慧選股頁面 (新增)
# ==========================================
def screener_page():
    st.title("🔍 智慧選股掃描")
    
    # 1. 範圍設定區
    st.subheader("1. 設定掃描範圍")
    
    # 選擇範圍
    scope_option = st.radio(
        "選擇股票池", 
        ["🏆 台灣 50 (權值股)", "💰 金融股清單 (金控/銀行)", "📝 自訂清單"], 
        horizontal=True
    )
    
    # 處理 scope 參數與自訂輸入
    scope_code = "TW50"
    custom_tickers = []
    
    if "台灣 50" in scope_option:
        scope_code = "TW50"
        st.caption("掃描台股權值最大的 50 檔股票。")
    elif "金融股" in scope_option:
        scope_code = "Finance"
        st.caption("掃描主要的金控與銀行股。")
    else:
        scope_code = "Custom"
        # 顯示文字輸入框
        user_input = st.text_area(
            "輸入股票代號 (用逗號或空白分隔)", 
            value="2330, 2454, 2603, 3034",
            help="例如: 2330 2317 2454"
        )
        # 解析使用者輸入
        if user_input:
            # 將逗號、換行都取代為空白，然後切割
            import re
            raw_list = re.split(r'[,\s\n]+', user_input)
            # 過濾空字串並去重
            custom_tickers = list(set([x.strip() for x in raw_list if x.strip()]))
            st.caption(f"目前共 {len(custom_tickers)} 檔股票待掃描。")

    st.divider()

    # 策略選擇區
    st.subheader("1. 選擇策略條件")
    
    col1, col2 = st.columns(2)
    with col1:
        s1 = st.checkbox("MA20 突破季線且站上半年線 (趨勢轉強)", value=True, key="s1")
        s2 = st.checkbox("KD 低檔黃金交叉 (短線買點)", key="s2")
        s3 = st.checkbox("均線多頭排列 (強勢股)", key="s3")
    with col2:
        s4 = st.checkbox("爆量長紅 (主力進場)", key="s4")
        s5 = st.checkbox("RSI 超賣 < 30 (搶反彈)", key="s5")

    # 收集選中的策略
    selected_strategies = []
    if s1: selected_strategies.append("MA_Cross_Major")
    if s2: selected_strategies.append("KD_Golden_Cross")
    if s3: selected_strategies.append("Bullish_Alignment")
    if s4: selected_strategies.append("Volume_Explosion")
    if s5: selected_strategies.append("RSI_Oversold")

    if st.button("🚀 開始掃描", type="primary"):
        if not selected_strategies:
            st.warning("請至少勾選一個策略！")
            return
        
        if scope_code == "Custom" and not custom_tickers:
            st.error("請輸入自訂股票代號！")
            return

        st.write("⏳ 正在掃描市場數據，請稍候 (約需 10-15 秒)...")
        progress_bar = st.progress(0)
        
        try:
            # 呼叫後端 API
            payload = {
                "strategies": selected_strategies,
                "scope": scope_code,
                "custom_tickers": custom_tickers if scope_code == "Custom" else []
            }
            # 假裝跑一下進度條讓使用者覺得有在動
            progress_bar.progress(30)
            
            res = requests.post(f"{BACKEND_URL}/api/screen", json=payload)
            progress_bar.progress(100)
            
            if res.status_code == 200:
                data = res.json()
                
                if not data:
                    st.warning("⚠️ 目前沒有股票符合您設定的條件。")
                else:
                    st.success(f"🎉 找到 {len(data)} 檔符合條件的股票！")
                    
                    # 整理成 DataFrame 顯示
                    df_res = pd.DataFrame(data)
                    # 把 list 轉成字串比較好顯示
                    df_res['matched_strategies'] = df_res['matched_strategies'].apply(lambda x: ", ".join(x))
                    
                    # 🔗 新增 Yahoo Finance 技術分析頁面連結
                    df_res['yahoo_url'] = df_res['stock_id'].apply(
                        lambda x: f"https://tw.stock.yahoo.com/quote/{x}.TW/technical-analysis"
                    )
                    
                    st.dataframe(
                        df_res,
                        column_config={
                            "yahoo_url": st.column_config.LinkColumn(
                                "技術分析",
                                help="點擊開啟 Yahoo 技術分析"
                            ),
                            "name": "名稱",
                            "close": "收盤價",
                            "matched_strategies": "符合條件",
                            "stock_id": None  # 隱藏原始股票代號欄位
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # 進階互動：點擊後直接跳轉去分析
                    st.divider()
                    st.markdown("### 👇 快速分析")
                    target = st.selectbox("選擇一檔股票進行 AI 分析", df_res['stock_id'])
                    
                    if st.button("分析這檔股票"):
                        # 這邊我們可以用 session_state 傳值並跳轉頁面
                        st.session_state['analysis_stock_id'] = target
                        st.switch_page("frontend/app.py") # 注意：如果你是單頁應用，這邊可能要改用 session_state 變數控制頁面切換
                        # 簡單一點的做法：
                        st.info(f"請複製代號 **{target}**，切換到「操盤分析」頁面輸入。")
            else:
                st.error(f"掃描失敗: {res.text}")
                
        except Exception as e:
            st.error(f"連線錯誤: {e}")

def backtest_page():
    st.title("🔙 智能策略回測")
    
    user = st.session_state.user_info
    
    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        # 選擇 AI 提供者
        #ai_provider = st.radio("選擇 AI 模型來源", ["Google Gemini (雲端)", "Ollama (本地)"], horizontal=True)
        ai_provider = st.radio("選擇 AI 模型來源", ["Ollama (本地)"], horizontal=True)
        provider_code = "gemini" if "Gemini" in ai_provider else "ollama"

    with col_set2:
        if provider_code == "gemini":
            # Gemini 設定
            saved_token = user.get("api_token") or ""
            api_key = st.text_input("Gemini API Key", value=saved_token, type="password")
            model_name = st.selectbox("模型版本", ["gemini-1.5-flash", "gemini-pro"])
        else:
            # Ollama 設定
            api_key = "ollama_no_key" # Ollama 不需要 Key，但後端需要字串
            # 這裡可以讓使用者自己輸入，或者寫死你有裝的模型
            model_name = st.text_input("Ollama 模型名稱", "gemma3:12b", help="請確保本地已執行 `ollama run <模型名>`")
            st.caption("⚠️ 須確保後端電腦已安裝 Ollama 並開啟服務 (port 11434)")
        # 🔥 新增策略風格選擇
        prompt_options = {
            "balanced": "⚖️ 平衡型 (穩健)",
            "aggressive": "🔥 激進型 (追高殺低)",
            "conservative": "🛡️ 保守型 (只買跌深)"
        }
        
        # 讓使用者選中文名稱，但我們後端只認英文 key
        selected_label = st.selectbox("AI 操盤風格", list(prompt_options.values()))
        # 反查回英文 key (例如 "aggressive")
        prompt_style = [k for k, v in prompt_options.items() if v == selected_label][0]

    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        stock_id = st.text_input("回測股票代號", "2330")
    with c2:
        capital = st.number_input("初始資金", value=100000, step=10000)

    if st.button("🚀 開始回測", type="primary"):
        if provider_code == "gemini" and not api_key:
            st.error("Gemini 模式需要 API Key")
            return
            
        with st.spinner(f"正在使用 {provider_code}/{model_name} 進行回測..."):
            try:
                payload = {
                    "user_id": user['id'],
                    "stock_id": stock_id,
                    "initial_capital": capital,
                    "api_key": api_key,
                    "provider": provider_code,
                    "model_name": model_name,
                    "prompt_style": prompt_style
                }
                res = requests.post(f"{BACKEND_URL}/api/backtest", json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    
                    if "error" in data:
                        st.error(data["error"])
                        return

                    # --- 顯示 KPI ---
                    kpi1, kpi2, kpi3 = st.columns(3)
                    kpi1.metric("初始資金", f"${data['initial_capital']:,}")
                    kpi2.metric("最終資產", f"${data['final_equity']:,}", delta=f"{data['total_return_pct']}%")
                    kpi3.metric("總交易次數", data['trade_count'])

                    # --- 繪製資產曲線 ---
                    st.subheader("📈 資產成長曲線")
                    ec_df = pd.DataFrame(data['equity_curve'])
                    ec_df['date'] = pd.to_datetime(ec_df['date'])
                    ec_df.set_index('date', inplace=True)
                    st.line_chart(ec_df['equity'])

                    # --- 顯示交易明細 ---
                    st.subheader("📋 交易明細")
                    if data['trades']:
                        trades_df = pd.DataFrame(data['trades'])
                        display_cols = [
                            'entry_date', 'exit_date', 'type', 
                            'entry_price', 'stop_loss', 'take_profit', 'exit_price', # 把 SL/TP 加在中間
                            'profit', 'profit_pct', 'reason'
                        ]
                        
                        st.dataframe(
                            trades_df[display_cols],
                            column_config={
                                "entry_date": "買入日期",
                                "exit_date": "賣出日期",
                                "type": "方向",
                                "entry_price": st.column_config.NumberColumn("買入價", format="%.2f"),
                                
                                # 🔥 新增這兩欄的設定
                                "stop_loss": st.column_config.NumberColumn("預設停損", format="%.2f"),
                                "take_profit": st.column_config.NumberColumn("預設停利", format="%.2f"),
                                
                                "exit_price": st.column_config.NumberColumn("賣出價", format="%.2f"),
                                "profit": st.column_config.NumberColumn("損益 (含稅)", format="$%d"),
                                "profit_pct": st.column_config.NumberColumn("報酬率", format="%.2f%%"),
                                "reason": "出場原因"
                            },
                            use_container_width=True
                        )
                    else:
                        st.info("這段期間 AI 選擇觀望，沒有進行任何交易。")
                else:
                    st.error(f"回測失敗: {res.text}")
            except Exception as e:
                st.error(f"連線錯誤: {e}")

# ==========================================
#  頁面 F: 回測儀表板 (新增)
# ==========================================
def backtest_dashboard_page():
    stock_options = []
    try:
        res = requests.get(f"{BACKEND_URL}/api/backtest/stocks")
        if res.status_code == 200:
            stock_options = res.json()
    except Exception as e:
        st.error(f"無法取得股票清單: {e}")

    # --- 2. 顯示下拉選單 ---
    if not stock_options:
        st.warning("⚠️ 目前資料庫中沒有任何回測紀錄，請先去「智能回測」頁面跑幾次。")
        return

    col1, col2 = st.columns([3, 1])
    with col1:
        # 改用 selectbox，預設選第一個
        target_stock = st.selectbox("選擇已回測的股票", stock_options)
    
    with col2:
        # 其實 selectbox 選了就會變，按鈕可以當作「強制重新整理」
        refresh_btn = st.button("🔄 重新載入", type="secondary")

    # 使用 session_state 暫存該股票的詳細紀錄
    # 當股票改變 (target_stock) 或 按下重新整理 (refresh_btn) 時，重新抓取資料
    if "dashboard_stock" not in st.session_state:
        st.session_state.dashboard_stock = ""

    # 判斷是否需要重新抓取資料
    should_fetch = (target_stock != st.session_state.dashboard_stock) or refresh_btn
    
    if should_fetch:
        try:
            params = {"stock_id": target_stock}
            res = requests.get(f"{BACKEND_URL}/api/backtest/history", params=params)
            
            if res.status_code == 200:
                st.session_state.history_data = res.json()
                st.session_state.dashboard_stock = target_stock # 更新目前狀態
            else:
                st.error("無法取得詳細資料")
        except Exception as e:
            st.error(f"連線錯誤: {e}")

    # --- 3. 顯示結果與比較 (這部分跟原本一樣，不用動) ---
    records = st.session_state.get("history_data", [])
    
    if not records:
        st.write("查無資料。")
        return

    st.divider()
    st.subheader(f"找到 {len(records)} 筆紀錄 ({target_stock})，請勾選要比較的項目：")
    
    # 整理資料給表格顯示
    table_data = []
    for r in records:
        # result_data 已經被 Pydantic 轉成 dict 了
        res = r['result_data']
        clean_strategy_name = r['strategy_name'].replace("Backtest_", "")
        table_data.append({
            "id": r['id'],
            "strategy": clean_strategy_name, # 這裡會顯示 Backtest_gemini_... 或 Backtest_ollama_...
            "return": res.get('total_return_pct', 0),
            "final_equity": res.get('final_equity', 0),
            "trades": res.get('trade_count', 0),
            "date": pd.to_datetime(r['created_at']).strftime('%Y-%m-%d %H:%M'),
            "raw_data": res # 暫存原始資料供繪圖用
        })
    
    df_table = pd.DataFrame(table_data)
    
    # 使用 AgGrid 或簡單的 dataframe 加上 checkbox (這裡用 multiselect 比較簡單)
    options = df_table.apply(lambda x: f"[{x['date']}] {x['strategy']} (報酬率: {x['return']}%)", axis=1).tolist()
    
    selected_indices = st.multiselect("選擇要 PK 的模型紀錄 (可多選)", options, default=options[:len(records)])
    
    if selected_indices:
        # 找出使用者選了哪些 row
        selected_rows = []
        for opt in selected_indices:
            # 反查原始資料
            idx = options.index(opt)
            selected_rows.append(df_table.iloc[idx])
            
        # --- 比較區塊 1: 績效長條圖 ---
        st.subheader("🏆 績效 PK")
        compare_df = pd.DataFrame(selected_rows)
        
        # 顯示比較表格
        st.dataframe(
            compare_df[['strategy', 'return', 'final_equity', 'trades', 'date']],
            column_config={
                "strategy": "使用模型",
                "return": st.column_config.NumberColumn("報酬率 %", format="%.2f%%"),
                "final_equity": st.column_config.NumberColumn("最終資產", format="$%d"),
                "trades": "交易次數",
                "date": "回測時間"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 畫長條圖比較報酬率
        st.bar_chart(compare_df, x="strategy", y="return", color="strategy")

        # --- 比較區塊 2: 資產曲線疊加圖 ---
        st.subheader("📈 資產成長曲線疊加")
        
        # 整理所有選中紀錄的 equity curve
        combined_equity = pd.DataFrame()
        
        for index, row in compare_df.iterrows():
            # 取出這筆紀錄的資產曲線
            curve = row['raw_data']['equity_curve'] # list of dict
            temp_df = pd.DataFrame(curve)
            temp_df['date'] = pd.to_datetime(temp_df['date'])
            temp_df.set_index('date', inplace=True)
            
            # 重新以此策略名稱命名 column
            col_name = f"{row['strategy']} ({row['date']})"
            temp_df.rename(columns={'equity': col_name}, inplace=True)
            
            # 合併到大表
            if combined_equity.empty:
                combined_equity = temp_df
            else:
                combined_equity = combined_equity.join(temp_df, how='outer')

        # 填補空值 (forward fill) 避免線條斷掉
        combined_equity.fillna(method='ffill', inplace=True)
        
        st.line_chart(combined_equity)

        st.divider()
        st.subheader("📋 詳細交易紀錄比較")

        # compare_df 是上面已經整理好，使用者勾選要 PK 的那幾筆資料
        # 我們直接遍歷它
        for index, row in compare_df.iterrows():
            
            # 設定摺疊標題
            expander_title = f"{row['strategy']} | {row['date']} | 報酬率: {row['return']}%"
            
            with st.expander(expander_title):
                # 從 raw_data 取出交易列表
                trades_list = row['raw_data'].get('trades', [])
                
                if trades_list:
                    df_trades = pd.DataFrame(trades_list)
                    
                    # 定義欄位順序 (包含停損停利)
                    # 使用 list comprehension 過濾掉舊資料可能沒有的欄位
                    desired_cols = [
                        'entry_date', 'exit_date', 'type', 
                        'entry_price', 'stop_loss', 'take_profit', 'exit_price', 
                        'profit', 'profit_pct', 'reason'
                    ]
                    final_cols = [c for c in desired_cols if c in df_trades.columns]

                    st.dataframe(
                        df_trades[final_cols],
                        column_config={
                            "entry_date": "買入日期",
                            "exit_date": "賣出日期",
                            "type": "方向",
                            "entry_price": st.column_config.NumberColumn("買入價", format="%.2f"),
                            "stop_loss": st.column_config.NumberColumn("停損", format="%.2f"),
                            "take_profit": st.column_config.NumberColumn("停利", format="%.2f"),
                            "exit_price": st.column_config.NumberColumn("賣出價", format="%.2f"),
                            "profit": st.column_config.NumberColumn("損益", format="$%d"),
                            "profit_pct": st.column_config.NumberColumn("報酬率", format="%.2f%%"),
                            "reason": "出場理由"
                        },
                        use_container_width=True
                    )
                else:
                    st.info("此策略在回測期間選擇觀望，沒有進行任何交易。")

# ==========================================
#  頁面 G: 自動化全策略回測 (新增)
# ==========================================
def auto_backtest_page():
    st.title("🤖 自動化策略矩陣回測")
    st.info("💡 系統將自動遍歷 [2種模型] x [4種策略] 共 12 次回測，並比較績效。")
    
    user = st.session_state.user_info

    # 1. 設定區
    c1, c2 = st.columns(2)
    with c1:
        stock_id = st.text_input("回測股票代號", "2330")
    with c2:
        capital = st.number_input("初始資金", value=100000, step=10000)

    # 設定要跑的模型與策略
    # 注意：這些模型必須已經在你的 Ollama 裡面 (ollama pull xxx)
    target_models = [
        "gpt-oss:20b", 
        "gemma3:12b"     
    ]
    
    target_strategies = {
        "balanced": "⚖️ 平衡型",
        "aggressive": "🔥 激進型",
        "conservative": "🛡️ 保守型",
        "standard": "🧑‍💼 標準型",
    }

    # Ollama URL 設定
    with st.expander("進階設定 (Ollama URL)"):
        ollama_url = st.text_input(
            "Ollama URL", 
            value="http://localhost:11434",
            help="如果是雲端部署，請填入 Ngrok 網址"
        )

    # 2. 執行區
    if st.button("🚀 啟動自動掃描", type="primary"):
        # 初始化 UI 元件
        progress_bar = st.progress(0)
        status_text = st.empty()
        timer_text = st.empty()
        result_area = st.container()
        
        # 計算總任務數
        total_tasks = len(target_models) * len(target_strategies)
        completed_tasks = 0
        start_time = time.time()
        
        all_results = []
        
        # 開始雙重迴圈
        for model in target_models:
            for style_key, style_label in target_strategies.items():
                
                # --- A. 更新狀態顯示 ---
                current_task_name = f"正在執行: {model} / {style_label} ..."
                status_text.markdown(f"**{current_task_name}**")
                
                # --- B. 呼叫後端 API ---
                task_start = time.time()
                try:
                    payload = {
                        "user_id": user['id'],
                        "stock_id": stock_id,
                        "initial_capital": capital,
                        "api_key": "ollama_no_key", # 本地模型不需要 Key
                        "provider": "ollama",
                        "model_name": model,
                        "ollama_url": ollama_url,
                        "prompt_style": style_key
                    }
                    
                    # 發送請求
                    res = requests.post(f"{BACKEND_URL}/api/backtest", json=payload)
                    
                    if res.status_code == 200:
                        data = res.json()
                        # 整理簡單結果存起來
                        all_results.append({
                            "Model": model,
                            "Strategy": style_label,
                            "Return %": data.get('total_return_pct', 0),
                            "Final Equity": data.get('final_equity', 0),
                            "Trades": data.get('trade_count', 0),
                            "raw_data": data # 存下來等等畫圖用
                        })
                    else:
                        st.error(f"❌ {model} 執行失敗: {res.text}")
                        
                except Exception as e:
                    st.error(f"❌ 連線錯誤: {e}")

                # --- C. 計算時間與更新進度 ---
                task_end = time.time()
                completed_tasks += 1
                
                # 計算進度 %
                progress = completed_tasks / total_tasks
                progress_bar.progress(progress)
                
                # 計算剩餘時間 (Simple Moving Average)
                elapsed_total = task_end - start_time
                avg_time_per_task = elapsed_total / completed_tasks
                remaining_tasks = total_tasks - completed_tasks
                eta_seconds = int(avg_time_per_task * remaining_tasks)
                
                # 格式化時間 (MM:SS)
                eta_str = f"{eta_seconds // 60:02d}:{eta_seconds % 60:02d}"
                elapsed_str = f"{int(elapsed_total) // 60:02d}:{int(elapsed_total) % 60:02d}"
                
                timer_text.info(f"⏳ 已用時間: {elapsed_str} | 預計剩餘時間: {eta_str} | 進度: {completed_tasks}/{total_tasks}")

        # 3. 掃描完成，顯示結果
        status_text.success("✅ 所有策略掃描完成！")
        timer_text.empty() # 清除計時器
        
        if all_results:
            df_res = pd.DataFrame(all_results)
            
            # --- 排行榜 ---
            st.subheader("🏆 績效排行榜")
            # 依照報酬率排序
            df_sorted = df_res.sort_values(by="Return %", ascending=False).reset_index(drop=True)
            
            # 標示出冠軍
            best = df_sorted.iloc[0]
            st.metric("最佳組合", f"{best['Model']} + {best['Strategy']}", f"{best['Return %']}%")
            
            st.dataframe(
                df_sorted[['Model', 'Strategy', 'Return %', 'Final Equity', 'Trades']],
                column_config={
                    "Return %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Final Equity": st.column_config.NumberColumn(format="$%d"),
                },
                use_container_width=True
            )

            # --- 視覺化比較 ---
            st.subheader("📊 績效熱力比較")
            # 畫一個長條圖比較
            # 為了讓圖表好看，組合一個名稱
            df_res['Combo'] = df_res['Model'] + " | " + df_res['Strategy']
            st.bar_chart(df_res, x='Combo', y='Return %', color='Strategy')
            
            # --- 資產曲線疊加 (選用) ---
            with st.expander("📈 查看資產曲線疊加圖"):
                combined_equity = pd.DataFrame()
                for item in all_results:
                    curve = item['raw_data']['equity_curve']
                    temp_df = pd.DataFrame(curve)
                    temp_df['date'] = pd.to_datetime(temp_df['date'])
                    temp_df.set_index('date', inplace=True)
                    
                    col_name = f"{item['Model']}-{item['Strategy']}"
                    temp_df.rename(columns={'equity': col_name}, inplace=True)
                    
                    if combined_equity.empty:
                        combined_equity = temp_df
                    else:
                        combined_equity = combined_equity.join(temp_df, how='outer')
                
                combined_equity.fillna(method='ffill', inplace=True)
                st.line_chart(combined_equity)
            st.divider()
            st.subheader("🔍 各組詳細交易明細")
            
            # 依照報酬率由高到低排序，讓表現最好的排前面
            sorted_results = sorted(all_results, key=lambda x: x['Return %'], reverse=True)

            for item in sorted_results:
                # 設定摺疊選單的標題 (模型 + 策略 + 報酬率)
                expander_label = f"🏆 {item['Model']} | {item['Strategy']} : 報酬率 {item['Return %']}% (交易 {item['Trades']} 次)"
                
                with st.expander(expander_label):
                    # 取出原始交易資料
                    trades_list = item['raw_data'].get('trades', [])
                    
                    if trades_list:
                        df_trades = pd.DataFrame(trades_list)
                        
                        # 確保欄位存在 (避免有些舊資料沒有 stop_loss 導致報錯)
                        # 定義我們想要顯示的順序
                        desired_cols = [
                            'entry_date', 'exit_date', 'type', 
                            'entry_price', 'stop_loss', 'take_profit', 'exit_price', 
                            'profit', 'profit_pct', 'reason'
                        ]
                        # 只選取 DataFrame 中實際存在的欄位
                        final_cols = [c for c in desired_cols if c in df_trades.columns]

                        st.dataframe(
                            df_trades[final_cols],
                            column_config={
                                "entry_date": "買入日期",
                                "exit_date": "賣出日期",
                                "type": "方向",
                                "entry_price": st.column_config.NumberColumn("買入價", format="%.2f"),
                                "stop_loss": st.column_config.NumberColumn("停損", format="%.2f"),
                                "take_profit": st.column_config.NumberColumn("停利", format="%.2f"),
                                "exit_price": st.column_config.NumberColumn("賣出價", format="%.2f"),
                                "profit": st.column_config.NumberColumn("損益", format="$%d"),
                                "profit_pct": st.column_config.NumberColumn("報酬率", format="%.2f%%"),
                                "reason": "出場理由"
                            },
                            use_container_width=True
                        )
                    else:
                        st.info("此組合在回測期間選擇觀望，沒有進行任何交易。")
# ==========================================
#  主導航控制器 (Navigation)
# ==========================================
def main_controller():
    # 側邊欄：顯示使用者資訊與頁面選單
    with st.sidebar:
        st.write(f"👤 您好，**{st.session_state.user_info['username']}**")
        
        # 頁面切換選單
        page = st.radio("前往頁面", 
            ["📈 操盤分析", "🔍 智慧選股", "🔙 智能回測", "🤖 自動化回測", "📊 回測儀表板", "📜 歷史紀錄", "👤 個人設定"]
        )
        
        st.divider()
        if st.button("🚪 登出"):
            # 清除 Cookie
            cookies["user_id"] = ""
            cookies["logged_in"] = ""
            cookies.save()
            
            # 清除 Session State
            st.session_state.logged_in = False
            st.session_state.user_info = {}
            st.rerun()

    # 根據選單顯示對應頁面
    if page == "📈 操盤分析":
        analysis_page()
    elif page == "🔍 智慧選股":  # <--- 新增路由
         screener_page()
    elif page == "📜 歷史紀錄":  # <--- 新增路由
        history_page()
    elif page == "🔙 智能回測": # 原本的 backtest_page
        backtest_page()
    elif page == "🤖 自動化回測": # <--- 新增路由
        auto_backtest_page()
    elif page == "📊 回測儀表板": # <--- 新增
        backtest_dashboard_page()
    elif page == "👤 個人設定":
        settings_page()

# ==========================================
#  程式進入點
# ==========================================
if st.session_state.logged_in:
    main_controller()
else:
    login_page()