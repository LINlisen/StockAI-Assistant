# frontend/app.py
import streamlit as st
import requests
import pandas as pd
import mplfinance as mpf

if "BACKEND_URL" in st.secrets:
    BACKEND_URL = st.secrets["BACKEND_URL"]  # 這是給雲端用的
else:
    BACKEND_URL = "http://127.0.0.1:8000"    # 這是給你本機測試用的

st.set_page_config(page_title="台股 AI 操盤系統", layout="wide")

# --- 初始化 Session State ---
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
def analysis_page():
    st.title("📈 台股 AI 操盤分析師")
    
    user = st.session_state.user_info
    
    # --- 自動帶入 API Key 的邏輯 ---
    # 從 session 取出 db 存的 token
    saved_token = user.get("api_token") or ""

# 側邊欄
    with st.sidebar:
        st.header("⚙️ 參數設定")
        
        # 1. API Key 輸入
        api_key_input = st.text_input(
            "Gemini API Key", 
            value=saved_token, 
            type="password"
        )
        
        # 2. 模型選擇邏輯
        # 為了避免每次畫面刷新都去敲後端 API，我們用 session_state 存起來
        if "model_list" not in st.session_state:
            st.session_state.model_list = ["models/gemini-2.0-flash"] # 預設值

        # 當有 API Key 且按下重新整理按鈕，或是剛載入時嘗試獲取
        col_m1, col_m2 = st.columns([4, 1])
        if col_m2.button("🔄", help="更新模型列表"):
            if api_key_input:
                try:
                    res = requests.post(f"{BACKEND_URL}/api/models", json={"api_key": api_key_input})
                    if res.status_code == 200:
                        st.session_state.model_list = res.json()
                        st.success("已更新")
                except:
                    st.warning("無法連線")
        
        # 下拉選單
        selected_model = col_m1.selectbox("選擇 AI 模型", st.session_state.model_list, index=0)

        st.divider()

        stock_id = st.text_input("股票代號", "2330")
        mode = st.selectbox("操作方向", ["做多", "做空"])
        cost = st.number_input("成本", 0.0)
        run_btn = st.button("🚀 開始分析", type="primary")


    if run_btn:
        if not api_key_input:
            st.error("請輸入 API Key")
            return
            
        with st.spinner(f"正在呼叫 {selected_model} 進行分析..."):
            try:
                payload = {
                    "user_id": user['id'],
                    "stock_id": stock_id,
                    "mode": mode,
                    "cost": cost,
                    "api_key": api_key_input,
                    "model_name": selected_model  # <--- 將選到的模型傳給後端
                }
                res = requests.post(f"{BACKEND_URL}/api/analyze", json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    # ... (後面的顯示邏輯不變) ...
                    col1, col2 = st.columns(2)
                    col1.metric("現價", f"{data['current_price']:.2f}")
                    col1.metric("趨勢", data['trend'])
                    
                    st.subheader(f"🧠 AI 分析報告 ({selected_model})") # 標題顯示使用的模型
                    st.info(data['ai_analysis'])
                    
                    raw = data['technical_data']
                    df = pd.DataFrame(raw)
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    st.line_chart(df['Close'])
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
#  主導航控制器 (Navigation)
# ==========================================
def main_controller():
    # 側邊欄：顯示使用者資訊與頁面選單
    with st.sidebar:
        st.write(f"👤 您好，**{st.session_state.user_info['username']}**")
        
        # 頁面切換選單
        page = st.radio("前往頁面", ["📈 操盤分析", "📜 歷史紀錄", "👤 個人設定"])
        
        st.divider()
        if st.button("登出"):
            st.session_state.logged_in = False
            st.session_state.user_info = {}
            st.rerun()

    # 根據選單顯示對應頁面
    if page == "📈 操盤分析":
        analysis_page()
    elif page == "📜 歷史紀錄":  # <--- 新增路由
        history_page()
    elif page == "👤 個人設定":
        settings_page()

# ==========================================
#  程式進入點
# ==========================================
if st.session_state.logged_in:
    main_controller()
else:
    login_page()