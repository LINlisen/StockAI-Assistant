#!/bin/bash

# StockAI-Assistant 系統啟動腳本
# 此腳本會啟動後端 (FastAPI)、前端 (Streamlit) 以及 Ollama 服務

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 顯示說明訊息
show_help() {
    echo -e "${CYAN}=========================================${NC}"
    echo -e "${CYAN}  台股 AI 操盤系統 - 啟動腳本說明${NC}"
    echo -e "${CYAN}=========================================${NC}"
    echo ""
    echo "用法:"
    echo "  ./startsys.sh [選項]"
    echo ""
    echo "選項:"
    echo "  -h, --help         顯示此說明訊息"
    echo "  --skip-ollama      跳過 Ollama 服務啟動"
    echo ""
    echo "範例:"
    echo "  ./startsys.sh              # 啟動所有服務"
    echo "  ./startsys.sh --help       # 顯示說明"
    echo "  ./startsys.sh --skip-ollama # 只啟動前後端，不啟動 Ollama"
    echo "  ./startsys.sh postgres-db   # 啟動指定名稱的資料庫容器"
    echo "  ./startsys.sh --skip-ollama postgres-db # 組合使用"
    echo ""
    echo "服務說明:"
    echo "  • 後端 API (FastAPI)    - http://127.0.0.1:8000"
    echo "  • 前端介面 (Streamlit)  - http://localhost:8501"
    echo "  • Ollama 本地 AI        - http://localhost:11434"
    echo ""
    echo "停止服務:"
    echo "  按 Ctrl+C 停止所有服務"
    echo ""
    exit 0
}

# 參數處理
SKIP_OLLAMA=false
DB_CONTAINER_NAME="postgres-container-custom-stockai"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        --skip-ollama)
            SKIP_OLLAMA=true
            shift
            ;;
        *)
            # 假設非 flag 的參數是資料庫容器名稱
            if [[ "$1" == -* ]]; then
                echo "未知選項: $1"
                echo "使用 -h 或 --help 查看說明"
                exit 1
            else
                DB_CONTAINER_NAME="$1"
                shift
            fi
            ;;
    esac
done

echo -e "${CYAN}=========================================${NC}"
echo -e "${CYAN}  台股 AI 操盤系統 - 系統啟動中...${NC}"
echo -e "${CYAN}=========================================${NC}"
echo ""

# 1. 啟動 Ollama 服務
if [ "$SKIP_OLLAMA" = true ]; then
    echo -e "${YELLOW}[1/3] 跳過 Ollama 服務 (使用 --skip-ollama 參數)${NC}"
else
    echo -e "${BLUE}[1/3] 啟動 Ollama 服務...${NC}"
    if command -v ollama &> /dev/null; then
        # 檢查 Ollama 是否已經在運行
        if pgrep -x "ollama" > /dev/null; then
            echo -e "${GREEN}✓ Ollama 已在運行中${NC}"
        else
            echo "正在啟動 Ollama..."
            ollama serve &
            sleep 3
            echo -e "${GREEN}✓ Ollama 啟動完成 (http://localhost:11434)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 未檢測到 Ollama，跳過此步驟${NC}"
        echo "  如需使用本地 AI 模型，請先安裝 Ollama: https://ollama.ai"
    fi
fi



echo ""

# 2. 啟動資料庫 (如果有指定容器名稱)
if [ -n "$DB_CONTAINER_NAME" ]; then
    echo -e "${BLUE}[2/3] 啟動資料庫容器 ($DB_CONTAINER_NAME)...${NC}"
    if command -v docker &> /dev/null; then
        if docker ps -a --format '{{.Names}}' | grep -Eq "^${DB_CONTAINER_NAME}$"; then
            if docker ps --format '{{.Names}}' | grep -Eq "^${DB_CONTAINER_NAME}$"; then
                 echo -e "${GREEN}✓ 資料庫容器 $DB_CONTAINER_NAME 已在運行中${NC}"
            else
                 echo "正在啟動 docker 容器..."
                 docker start "$DB_CONTAINER_NAME"
                 echo -e "${GREEN}✓ 資料庫容器啟動完成${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ 找不到名稱為 $DB_CONTAINER_NAME 的容器${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 未檢測到 Docker，無法啟動資料庫${NC}"
    fi
    echo ""
fi

# 2. 啟動後端 API (FastAPI)
echo -e "${BLUE}[2/3] 啟動後端 API (FastAPI)...${NC}"
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✓ 後端啟動完成 (PID: $BACKEND_PID)${NC}"
echo "  API 位址: http://127.0.0.1:8000"
echo "  API 文件: http://127.0.0.1:8000/docs"
cd ..

echo ""

# 3. 啟動前端介面 (Streamlit)
echo -e "${BLUE}[3/3] 啟動前端介面 (Streamlit)...${NC}"
sleep 2  # 等待後端完全啟動
cd frontend
streamlit run app.py --server.port 8501 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ 前端啟動完成 (PID: $FRONTEND_PID)${NC}"
echo "  前端位址: http://localhost:8501"
cd ..

echo ""
echo "========================================="
echo -e "${GREEN}✓ 所有服務啟動完成！${NC}"
echo "========================================="
echo ""
echo "📊 服務狀態："
echo "  • 後端 API:  http://127.0.0.1:8000"
echo "  • 前端介面:  http://localhost:8501"
echo "  • Ollama:    http://localhost:11434"
echo ""
echo "💡 使用說明："
echo "  1. 開啟瀏覽器訪問前端: http://localhost:8501"
echo "  2. 註冊/登入帳號"
echo "  3. 設定 Gemini API Key (或使用 Ollama 本地模型)"
echo "  4. 開始使用 AI 操盤分析功能"
echo ""
echo "⚠️  停止服務："
echo "  按 Ctrl+C 停止所有服務"
echo ""

# 等待使用者中斷
wait
