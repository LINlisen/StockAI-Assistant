from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 1. 讀取 .env 檔案中的環境變數
load_dotenv()

# 2. 取得資料庫連線網址
# 請在專案根目錄的 .env 檔案中設定 DATABASE_URL
# 格式範例: postgresql://user:password@localhost:5432/stock_db
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 如果沒有設定環境變數，預設使用 SQLite (方便本地測試，但建議正式環境用 PostgreSQL)
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

# 3. 建立資料庫引擎
# check_same_thread 參數僅用於 SQLite，PostgreSQL 不需要
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True  
)

# 4. 建立 Session 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. 建立 Base 類別 (給 models.py 繼承用)
Base = declarative_base()

# 6. 依賴注入函數 (給 FastAPI 的路由使用)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()