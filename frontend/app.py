# frontend/app.py
import streamlit as st
import requests
import pandas as pd
import mplfinance as mpf

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
#  頁面 E: 智慧選股頁面 (新增)
# ==========================================
def screener_page():
    st.title("🔍 智慧選股掃描")
    st.info("💡 說明：系統將掃描「台灣 50」成分股，找出符合您勾選策略的股票。")

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

        st.write("⏳ 正在掃描市場數據，請稍候 (約需 10-15 秒)...")
        progress_bar = st.progress(0)
        
        try:
            # 呼叫後端 API
            payload = {
                "strategies": selected_strategies,
                "scope": "TW50"
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
                    
                    st.dataframe(
                        df_res,
                        column_config={
                            "stock_id": "股票代號",
                            "name": "名稱",
                            "close": "收盤價",
                            "matched_strategies": "符合條件"
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
        ai_provider = st.radio("選擇 AI 模型來源", ["Google Gemini (雲端)", "Ollama (本地)"], horizontal=True)
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
            model_name = st.text_input("Ollama 模型名稱", "llama3.2", help="請確保本地已執行 `ollama run <模型名>`")
            st.caption("⚠️ 須確保後端電腦已安裝 Ollama 並開啟服務 (port 11434)")
        # 🔥 新增策略風格選擇
        prompt_options = {
            "balanced": "⚖️ 平衡型 (穩健)",
            "aggressive": "🔥 激進型 (追高殺低)",
            "conservative": "🛡️ 保守型 (只買跌深)",
            "short_term": "⚡ 短線隔日沖"
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
# ==========================================
#  主導航控制器 (Navigation)
# ==========================================
def main_controller():
    # 側邊欄：顯示使用者資訊與頁面選單
    with st.sidebar:
        st.write(f"👤 您好，**{st.session_state.user_info['username']}**")
        
        # 頁面切換選單
        page = st.radio("前往頁面", 
            ["📈 操盤分析", "🔍 智慧選股", "🔙 智能回測", "📊 回測儀表板", "📜 歷史紀錄", "👤 個人設定"]
        )
        
        st.divider()
        if st.button("登出"):
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