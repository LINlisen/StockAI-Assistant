# StockAI-Assistant (台股 AI 操盤系統)

這是一個結合 FastAPI 後端與 Streamlit 前端的台股 AI 輔助操盤系統。整合了 Google Gemini AI 與技術分析指標，提供智慧選股、個股分析、以及回測功能。

## ✨ 功能特色

*   **AI 操盤分析**: 結合技術指標 (MA, KD, RSI, MACD) 與 Gemini AI，提供個股操作建議。
*   **智慧選股**: 掃描市場 (如台灣 50)，根據策略 (均線突破、KD 黃金交叉等) 篩選潛力股。
*   **智能回測**: 針對個股進行歷史回測，比較不同 AI 模型與策略的績效。
*   **回測儀表板**: 視覺化比較不同回測紀錄的資產曲線與績效數據。
*   **歷史紀錄**: 自動儲存使用者的查詢與分析結果。
*   **使用者系統**: 支援註冊、登入與個人 API Key 管理。

## 🛠️ 系統需求

*   **Python**: 3.8 或以上版本
*   **資料庫**: 預設使用 SQLite (內建)，可自行配置 PostgreSQL。
*   **AI 模型**:
    *   Google Gemini API Key (必備)
    *   Ollama (選用，若需使用本地模型)

## 🚀 安裝教學

### 1. 複製專案

```bash
git clone https://github.com/your-repo/StockAI-Assistant.git
cd StockAI-Assistant
```

### 2. 安裝依賴套件

建議使用虛擬環境 (Virtualenv)：

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows)
venv\Scripts\activate

# 啟動虛擬環境 (Mac/Linux)
source venv/bin/activate
```

安裝所需套件：

```bash
pip install -r requirements.txt
```

### 3. 環境設定 (.env)

在專案根目錄建立 `.env` 檔案，並設定以下變數 (若使用預設 SQLite 可跳過資料庫設定)：

```env
# 資料庫連線 (預設 SQLite，若要用 Postgres 請修改)
# DATABASE_URL=postgresql://user:password@localhost:5432/stock_db

# 其他設定 (視需求而定)
```

## 🖥️ 啟動應用程式

本系統分為後端 (FastAPI) 與前端 (Streamlit)，需分別啟動。

### 步驟 1: 啟動後端 API

開啟一個終端機視窗，執行：

```bash
uvicorn backend.main:app --reload
```
*   後端預設執行於: `http://127.0.0.1:8000`
*   API 文件 (Swagger UI): `http://127.0.0.1:8000/docs`

### 步驟 2: 啟動前端介面

開啟另一個終端機視窗，執行：

```bash
streamlit run frontend/app.py
```
*   前端預設執行於: `http://localhost:8501`

## 📖 使用說明

1.  **註冊/登入**: 首次使用請先註冊帳號。
2.  **設定 API Key**: 登入後，建議在「個人設定」或側邊欄輸入您的 Google Gemini API Key，以便 AI 功能正常運作。
3.  **開始分析**:
    *   前往「操盤分析」輸入股票代號 (如 2330)。
    *   前往「智慧選股」勾選策略進行掃描。
    *   前往「智能回測」測試您的交易策略。

## 📂 專案結構

```
StockAI-Assistant/
├── backend/            # FastAPI 後端程式碼
│   ├── main.py         # 程式入口
│   ├── models.py       # 資料庫模型
│   ├── schemas.py      # Pydantic 驗證模型
│   ├── database.py     # 資料庫連線設定
│   └── services/       # 核心邏輯 (AI, 股票數據, 回測)
├── frontend/           # Streamlit 前端程式碼
│   └── app.py          # 前端主程式
├── requirements.txt    # 專案依賴套件
└── README.md           # 專案說明文件
```
