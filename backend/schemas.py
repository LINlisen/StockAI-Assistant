# backend/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# --- 原有的 Stock 相關 schema 保持不變 ---
class StockAnalysisRequest(BaseModel):
    user_id: int
    stock_id: str
    mode: str
    cost: float
    api_key: str
    model_name: str = "models/gemini-1.5-flash"  # 設定預設值
    
class AnalysisLogResponse(BaseModel):
    id: int
    stock_id: str
    mode: str
    cost_price: float
    current_price: float
    ai_advice: str
    created_at: datetime

    class Config:
        from_attributes = True # 讓 Pydantic 可以讀取 ORM 物件
class StockAnalysisResponse(BaseModel):
    stock_id: str
    current_price: float
    trend: str
    ai_analysis: str
    technical_data: Dict[str, Any]

# 新增：選股請求
class ScreenRequest(BaseModel):
    # 策略清單，例如 ["MA_Cross", "KD_Gold"]
    strategies: List[str] 
    # 掃描範圍，預設 "TW50" (台灣50)
    scope: str = "TW50" 

# 新增：選股結果 (單檔股票)
class ScreenResult(BaseModel):
    stock_id: str
    name: str # 股票名稱 (選填，目前 yfinance 抓名稱較慢，可先用代號)
    close: float
    matched_strategies: List[str] # 符合了哪些策略

# --- 新增：用來請求模型列表的格式 ---
class APIKeyRequest(BaseModel):
    api_key: str

# --- 新增 User 相關 schema ---

# 註冊請求
class UserCreate(BaseModel):
    username: str
    account: str
    password: str
    api_token: Optional[str] = None

# 登入請求
class UserLogin(BaseModel):
    account: str
    password: str

# 登入成功後回傳的資料
class UserResponse(BaseModel):
    id: int
    username: str
    account: str
    api_token: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None