# 反向查詢功能 - 輸入股票名稱顯示代號

## 功能說明
實現當用戶輸入股票名稱（例如：台積電）時，自動顯示對應的股票代號（2330）。

## 前置條件
✅ `stock_mapping.py` 已經包含反向查詢功能：
- `NAME_TO_SYMBOL` - 名稱到代號的對應表
- `get_stock_symbol(stock_name)` - 根據名稱取得代號的函數

這些功能已經在您的 `stock_mapping.py` 中實現了！

## 實作方式

### 方案一：使用兩個獨立輸入框（推薦）

在 `frontend/app.py` 的股票選擇區塊（約第 228-240 行），修改為：

```python
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
```

**優點**：
- 清楚分離兩種輸入方式
- 用戶可以選擇用代號或名稱輸入
- 提示用戶將找到的代號填入左側

**缺點**：
- 需要用戶手動複製代號到左側輸入框

---

### 方案二：使用 Session State 自動同步（進階）

如果想要自動同步，需要使用 `st.session_state`：

```python
        # --- 股票選擇 (支援雙向查詢 + 自動同步) ---
        st.divider()
        st.subheader("📊 股票選擇")
        
        # 初始化 session state
        if 'selected_stock_id' not in st.session_state:
            st.session_state.selected_stock_id = "2330"
        
        # 建立兩欄布局
        col1, col2 = st.columns(2)
        
        with col1:
            stock_id_input = st.text_input(
                "股票代號", 
                value=st.session_state.selected_stock_id, 
                key="stock_code_input",
                help="輸入股票代號，例如：2330"
            )
            
            # 如果用戶修改了代號，更新 session state
            if stock_id_input != st.session_state.selected_stock_id:
                st.session_state.selected_stock_id = stock_id_input
            
            # 顯示對應的股票名稱
            stock_name = get_stock_name(stock_id_input)
            if stock_name:
                st.success(f"✓ {stock_name}")
            else:
                st.warning("未知股票")
        
        with col2:
            stock_name_input = st.text_input(
                "或輸入股票名稱", 
                "", 
                key="stock_name_input",
                help="輸入股票名稱，例如：台積電"
            )
            
            # 如果用戶輸入了名稱，查詢代號並更新
            if stock_name_input:
                stock_symbol = get_stock_symbol(stock_name_input)
                if stock_symbol:
                    st.success(f"✓ 代號：{stock_symbol}")
                    # 更新 session state，左側會自動更新
                    if stock_symbol != st.session_state.selected_stock_id:
                        st.session_state.selected_stock_id = stock_symbol
                        st.rerun()  # 重新執行以更新左側輸入框
                else:
                    st.warning("未找到對應股票")
        
        # 使用 session_state 中的值作為最終的 stock_id
        stock_id = st.session_state.selected_stock_id
```

**優點**：
- 自動同步，用戶體驗更好
- 輸入名稱後，左側代號會自動更新

**缺點**：
- 程式碼較複雜
- 需要理解 Streamlit 的 session_state 機制

---

### 方案三：使用下拉選單（最簡單）

如果您希望用戶從列表中選擇，可以使用 `st.selectbox`：

```python
        # --- 股票選擇 (使用下拉選單) ---
        st.divider()
        st.subheader("📊 股票選擇")
        
        # 從 stock_mapping 取得所有股票
        from stock_mapping import get_all_stocks
        
        all_stocks = get_all_stocks()  # 返回 [(代號, 名稱), ...]
        
        # 建立選項列表：格式為 "代號 - 名稱"
        stock_options = [f"{code} - {name}" for code, name in all_stocks]
        
        # 下拉選單
        selected_option = st.selectbox(
            "選擇股票",
            stock_options,
            index=0,  # 預設選第一個
            help="可以搜尋代號或名稱"
        )
        
        # 從選項中提取股票代號
        stock_id = selected_option.split(" - ")[0]
        
        # 顯示選擇的股票資訊
        st.info(f"已選擇：{selected_option}")
```

**優點**：
- 最簡單，不會輸入錯誤
- Streamlit 的 selectbox 支援搜尋功能
- 用戶可以輸入代號或名稱進行搜尋

**缺點**：
- 如果股票很多，列表會很長
- 無法輸入不在列表中的股票

---

## 推薦方案

我推薦使用 **方案一（兩個獨立輸入框）**，因為：

1. ✅ 實作簡單
2. ✅ 功能清楚
3. ✅ 不需要複雜的狀態管理
4. ✅ 用戶可以自由選擇輸入方式

## 需要修改的地方

只需要修改 `frontend/app.py` 的一個地方：

**位置**：約第 228-240 行（股票選擇區塊）

**需要 import**：
```python
from stock_mapping import get_stock_name, get_stock_symbol  # 在檔案開頭
```

## 測試方式

修改完成後：

1. 啟動系統：`.\startsys.ps1`
2. 登入並進入「操盤分析」頁面
3. 測試代號輸入：
   - 左側輸入 "2330" → 應顯示 "✓ 台積電"
   - 左側輸入 "2317" → 應顯示 "✓ 鴻海"
4. 測試名稱輸入：
   - 右側輸入 "台積電" → 應顯示 "✓ 2330"
   - 右側輸入 "鴻海" → 應顯示 "✓ 2317"
   - 右側輸入 "不存在的股票" → 應顯示 "未找到對應股票"

## 注意事項

⚠️ **重要**：名稱必須完全匹配才能查詢成功

- ✅ "台積電" → 找到 2330
- ❌ "台積" → 找不到（不完全匹配）
- ❌ "台積電公司" → 找不到（多餘文字）

如果需要支援模糊搜尋，可以使用 `search_stock()` 函數（已在 `stock_mapping.py` 中實現）。
