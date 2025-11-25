# backend/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

# --- 原有的 Stock 相關 schema 保持不變 ---
class StockAnalysisRequest(BaseModel):
    stock_id: str
    mode: str
    cost: float
    api_key: str
    model_name: str = "models/gemini-1.5-flash"  # 設定預設值

class StockAnalysisResponse(BaseModel):
    stock_id: str
    current_price: float
    trend: str
    ai_analysis: str
    technical_data: Dict[str, Any]

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