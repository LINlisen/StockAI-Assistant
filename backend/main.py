# backend/main.py
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import hashlib

# 匯入我們剛寫好的模組
from database import get_db, engine
import models
import schemas
from services.stock_service import StockService
from services.ai_service import AIService
from services.backtest_service import BacktestService

# 初始化 DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 初始化 Service 實例
stock_service = StockService()
ai_service = AIService()
backtest_service = BacktestService()

# --- 工具函式：SHA256 加密 ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- 1. 使用者註冊 API ---
@app.post("/api/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 檢查帳號是否已存在
    existing_user = db.query(models.User).filter(models.User.account == user.account).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="此帳號已被註冊")
    
    # 建立新使用者
    new_user = models.User(
        username=user.username,
        account=user.account,
        password_hash=hash_password(user.password), # 儲存雜湊值
        api_token=user.api_token
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/api/models")
def get_models(req: schemas.APIKeyRequest):
    models = ai_service.get_available_models(req.api_key)
    if not models:
        # 如果抓不到，回傳一組預設的給前端當備案
        return ["models/gemini-1.5-flash", "models/gemini-pro", "models/gemini-1.5-pro"]
    return models


# --- 2. 使用者登入 API ---
@app.post("/api/login", response_model=schemas.UserResponse)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    # 根據帳號尋找使用者
    user = db.query(models.User).filter(models.User.account == user_data.account).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="帳號或密碼錯誤") # 安全起見，不提示具體哪個錯
        
    # 比對密碼 (將輸入的密碼雜湊後與資料庫比對)
    if user.password_hash != hash_password(user_data.password):
        raise HTTPException(status_code=400, detail="帳號或密碼錯誤")
        
    return user

@app.post("/api/analyze", response_model=schemas.StockAnalysisResponse)
def analyze_stock(req: schemas.StockAnalysisRequest, db: Session = Depends(get_db)):
    try:
        # 1. 獲取並計算數據
        df = stock_service.fetch_data(req.stock_id)
        df_calculated = stock_service.calculate_indicators(df)
        
        # 2. 產生摘要數據
        summary = stock_service.get_technical_summary(df_calculated)
        
        # 3. 呼叫 AI
        ai_result = ai_service.get_analysis(
             api_key=req.api_key,
            stock_id=req.stock_id,
            mode=req.mode,
            cost=req.cost,
            context_data=summary["context_str"],
            model_name=req.model_name
        )

        # 4. 存入資料庫 (PostgreSQL)
        db_log = models.AnalysisLog(
            user_id=req.user_id,
            stock_id=req.stock_id,
            mode=req.mode,
            cost_price=req.cost,
            current_price=float(summary["close"]), 
            ai_advice=ai_result
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)

        # 5. 準備回傳給前端的圖表數據
        # 將 DataFrame 索引轉為字串以便 JSON 傳輸
        chart_data = df_calculated.reset_index()
        chart_data['Date'] = chart_data['Date'].astype(str) 
        # 為了傳輸效率，通常只回傳最近 100-200 筆，或全部回傳視需求而定
        chart_data_dict = chart_data.tail(150).to_dict(orient='list')

        return schemas.StockAnalysisResponse(
            stock_id=req.stock_id,
            current_price=float(summary["close"]), 
            trend=summary["trend"],
            ai_analysis=ai_result,
            technical_data=chart_data_dict
        )

    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"系統錯誤: {str(e)}")
    

@app.post("/api/screen", response_model=List[schemas.ScreenResult])
def screen_stocks(req: schemas.ScreenRequest, db: Session = Depends(get_db)):
    try:
        # 如果使用者沒選任何策略，就預設全部檢查
        target_strategies = req.strategies if req.strategies else ["MA_Cross_Major", "KD_Golden_Cross"]
        
        # 執行選股
        results = stock_service.screen_stocks(target_strategies)
        
        return results
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{user_id}", response_model=List[schemas.AnalysisLogResponse])
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    # 根據 user_id 查詢，並依時間倒序排列 (最新的在前面)
    logs = db.query(models.AnalysisLog)\
             .filter(models.AnalysisLog.user_id == user_id)\
             .order_by(models.AnalysisLog.created_at.desc())\
             .all()
    return logs

@app.put("/api/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    # 1. 找人
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="使用者不存在")

    # 2. 更新欄位 (如果有傳值才更新)
    if user_update.username:
        db_user.username = user_update.username
    
    if user_update.api_token:
        # 允許使用者清空 Token (如果傳入空字串)
        db_user.api_token = user_update.api_token
        
    if user_update.password:
        # 如果有新密碼，記得要重新雜湊
        db_user.password_hash = hash_password(user_update.password)

    # 3. 存檔
    db.commit()
    db.refresh(db_user)
    
    return db_user



@app.post("/api/backtest")
def run_backtest_api(req: schemas.BacktestRequest, db: Session = Depends(get_db)):
    try:
        result = backtest_service.run_backtest(
            db=db,
            api_key=req.api_key,
            stock_id=req.stock_id,
            initial_capital=req.initial_capital,
            provider=req.provider,      # <--- 傳入
            model_name=req.model_name,   # <--- 傳入
            prompt_style=req.prompt_style
        )
        return result
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/backtest/history", response_model=List[schemas.BacktestHistoryItem])
def get_backtest_history(stock_id: str = None, db: Session = Depends(get_db)):
    # 如果前端有傳 stock_id 就篩選，沒有就回傳全部
    return backtest_service.get_history(db, stock_id)

@app.get("/api/backtest/stocks", response_model=List[str])
def get_backtest_stock_list(db: Session = Depends(get_db)):
    try:
        return backtest_service.get_tested_stocks(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))