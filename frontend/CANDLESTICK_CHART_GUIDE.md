# 請在 app.py 中進行以下修改

## 修改 1: 在側邊欄加入圖表配色選擇器

找到約第 262-263 行：
```python
cost = st.number_input("成本", 0.0)
run_btn = st.button("🚀 開始分析", type="primary")
```

替換為：
```python
cost = st.number_input("成本", 0.0)

# 圖表配色選擇
st.divider()
chart_style = st.selectbox(
    "📊 K線圖配色",
    ["紅綠配色 (漲紅跌綠)", "黑白配色 (漲白跌黑)"],
    help="選擇 K 線圖的配色方案"
)

run_btn = st.button("🚀 開始分析", type="primary")
```

## 修改 2: 將折線圖改為 K 線圖

找到約第 305-311 行：
```python
# 繪圖
if data.get('technical_data'):
    raw = data['technical_data']
    df = pd.DataFrame(raw)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    st.line_chart(df['Close'])
```

替換為：
```python
# 繪製 K 線圖
if data.get('technical_data'):
    raw = data['technical_data']
    df = pd.DataFrame(raw)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # 確保有 OHLC 資料
    required_cols = ['Open', 'High', 'Low', 'Close']
    if all(col in df.columns for col in required_cols):
        st.subheader("📈 K 線圖")
        
        # 根據使用者選擇的配色方案設定樣式
        if "紅綠" in chart_style:
            # 台灣習慣：漲紅跌綠
            mc = mpf.make_marketcolors(
                up='red',      # 上漲為紅色
                down='green',  # 下跌為綠色
                edge='inherit',
                wick='inherit',
                volume='in'
            )
        else:
            # 黑白配色：漲白跌黑
            mc = mpf.make_marketcolors(
                up='white',    # 上漲為白色
                down='black',  # 下跌為黑色
                edge='black',
                wick='black',
                volume='in'
            )
        
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=False)
        
        # 繪製 K 線圖
        fig, axes = mpf.plot(
            df,
            type='candle',      # K 線圖
            style=s,
            title=f'{stock_id} K線圖',
            ylabel='價格 (TWD)',
            volume=True if 'Volume' in df.columns else False,
            figsize=(12, 6),
            returnfig=True
        )
        
        st.pyplot(fig)
    else:
        # 如果沒有完整 OHLC 資料，顯示折線圖
        st.subheader("📈 收盤價走勢")
        st.line_chart(df['Close'])
```

## 說明

1. **配色選擇器**: 在側邊欄新增下拉選單，讓使用者選擇紅綠或黑白配色
2. **K 線圖**: 使用 `mplfinance` 繪製專業的燭台圖
3. **配色方案**:
   - 紅綠配色：漲紅跌綠（台灣習慣）
   - 黑白配色：漲白跌黑
4. **容錯處理**: 如果沒有完整 OHLC 資料，自動降級為折線圖
