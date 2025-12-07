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
(目前沒有SQLITE，要自己建一下PG，請在專案根目錄建立 .env 檔案)

在專案根目錄建立 `.env` 檔案，並設定以下變數 (若使用預設 SQLite 可跳過資料庫設定)：

```env
# 資料庫連線 (預設 SQLite，若要用 Postgres 請修改)
# DATABASE_URL=postgresql://user:password@localhost:5432/stock_db

# 其他設定 (視需求而定)
```

## 🖥️ 啟動應用程式

### 🚀 方法一：一鍵啟動 (推薦)

我們提供了自動化啟動腳本，可同時啟動後端、前端與 Ollama 服務。
記得先進入 venv

#### Windows (PowerShell)：

```powershell
# 啟動所有服務
.\startsys.ps1

# 查看說明
.\startsys.ps1 -help

# 只啟動前後端，跳過 Ollama
.\startsys.ps1 -skipOllama

# 停止所有服務
.\stopsys.ps1
```

> **💡 提示**：首次執行可能需要設定執行權限：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### Linux / Mac / Git Bash：

```bash
# 給予執行權限 (首次使用)
chmod +x startsys.sh

# 啟動所有服務
./startsys.sh

# 查看說明
./startsys.sh --help

# 只啟動前後端，跳過 Ollama
./startsys.sh --skip-ollama

# 停止服務：按 Ctrl+C
```

---

### 📋 方法二：手動分別啟動

如果您想要分別控制各個服務，可以手動啟動：

#### 步驟 1: 啟動後端 API

開啟一個終端機視窗，執行：

```bash
cd backend
uvicorn main:app --reload
```
*   後端預設執行於: `http://127.0.0.1:8000`
*   API 文件 (Swagger UI): `http://127.0.0.1:8000/docs`

#### 步驟 2: 啟動前端介面

開啟另一個終端機視窗，執行：

```bash
cd frontend
streamlit run app.py
```
*   前端預設執行於: `http://localhost:8501`

#### 步驟 3: 啟動 Ollama (選用)

如需使用本地 AI 模型：

```bash
ollama serve
```
*   Ollama 預設執行於: `http://localhost:11434`

---

### 📊 服務狀態確認

啟動成功後，您可以訪問以下網址：

| 服務 | 網址 | 說明 |
|------|------|------|
| **前端介面** | http://localhost:8501 | Streamlit 使用者介面 |
| **後端 API** | http://127.0.0.1:8000 | FastAPI 後端服務 |
| **API 文件** | http://127.0.0.1:8000/docs | Swagger UI 互動式文件 |
| **Ollama** | http://localhost:11434 | 本地 AI 模型服務 (選用) |

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
