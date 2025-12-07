# 股票名稱動態顯示 - 修改說明

## 問題
目前使用 `st.text_input(..., disabled=True)` 無法實現動態更新，因為 Streamlit 不會重新渲染 disabled 的輸入欄位。

## 解決方案
改用 `st.info()` 或 `st.markdown()` 來顯示股票名稱，這樣可以實現即時動態更新。

## 修改步驟

### 步驟 1: 加入 import（已完成）
```python
from stock_mapping import get_stock_name
```

### 步驟 2: 修改股票選擇區塊

找到 `frontend/app.py` 中約第 223-242 行的這段代碼：

```python
        selected_style_label = st.selectbox("分析風格", list(style_options.values()))
        prompt_style = [k for k, v in style_options.items() if v == selected_style_label][0]
        # # --- 通用參數 ---
        # stock_id = st.text_input("股票代號", "2330")

        # --- 股票選擇 (新增自動顯示名稱功能) ---
        st.subheader("📊 股票選擇")
        col_stock1, col_stock2 = st.columns([2, 3])
        
        with col_stock1:
            stock_id = st.text_input("股票代號", "2330", key="stock_code_input")
        
        with col_stock2:
            # 自動顯示股票名稱
            stock_name = get_stock_name(stock_id)
            if stock_name:
                st.text_input("股票名稱", value=stock_name, disabled=True, key="stock_name_display")
            else:
                st.text_input("股票名稱", value="(未知股票)", disabled=True, key="stock_name_display_unknown")
```

**替換為：**

```python
        selected_style_label = st.selectbox("分析風格", list(style_options.values()))
        prompt_style = [k for k, v in style_options.items() if v == selected_style_label][0]
        
        # --- 股票選擇 (新增自動顯示名稱功能) ---
        st.divider()
        st.subheader("📊 股票選擇")
        
        stock_id = st.text_input("股票代號", "2330", key="stock_code_input")
        
        # 自動顯示股票名稱（使用 info 實現動態更新）
        stock_name = get_stock_name(stock_id)
        if stock_name:
            st.info(f"**股票名稱：** {stock_name}")
        else:
            st.warning(f"**股票代號 {stock_id}** - 未在對應表中找到")
```

## 主要改動說明

1. **移除兩欄式布局**：不再使用 `st.columns()`
2. **使用 `st.info()` 顯示名稱**：當找到股票時，用藍色資訊框顯示
3. **使用 `st.warning()` 顯示未知**：當找不到股票時，用黃色警告框提示
4. **移除 disabled text_input**：改用 info/warning 元件，這些會自動重新渲染

## 效果

修改後，當用戶在「股票代號」輸入框中輸入或修改代號時：

- **輸入 "2330"** → 下方立即顯示藍色框：**股票名稱： 台積電**
- **輸入 "2317"** → 下方立即顯示藍色框：**股票名稱： 鴻海**
- **輸入 "9999"** → 下方立即顯示黃色框：**股票代號 9999 - 未在對應表中找到**

## 為什麼這樣可以動態更新？

- `st.info()` 和 `st.warning()` 是 Streamlit 的顯示元件，每次腳本重新執行時都會重新渲染
- 當用戶修改輸入框內容時，Streamlit 會重新執行整個腳本
- 新的 `stock_id` 值會被傳入 `get_stock_name()`，返回新的名稱
- `st.info()` 會顯示新的名稱

而 `st.text_input(..., disabled=True)` 不會動態更新，因為它的值在創建時就固定了。
