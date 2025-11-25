from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from .database import Base

# --- 新增 User 模型 ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String, unique=True, index=True)  # 帳號 (唯一)
    username = Column(String)                          # 使用者名稱
    password_hash = Column(String)                     # SHA256 加密後的密碼
    api_token = Column(String, nullable=True)          # Gemini API Key (選填)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class AnalysisLog(Base):
    """
    分析紀錄表 (analysis_logs)
    用來儲存每一次 AI 分析的結果，方便日後回測或查詢歷史紀錄。
    """
    __tablename__ = "analysis_logs"

    # 主鍵 ID，自動遞增
    id = Column(Integer, primary_key=True, index=True)
    
    # 股票代號 (例如: 2330.TW)，建立索引以加快搜尋速度
    stock_id = Column(String(20), index=True)
    
    # 操作方向 (例如: Long 做多 / Short 做空)
    mode = Column(String(10))
    
    # 使用者輸入的持倉成本
    cost_price = Column(Float)
    
    # 分析當下的股票現價
    current_price = Column(Float)
    
    # Gemini AI 給出的完整分析建議 (Text 類型可存長文字)
    ai_advice = Column(Text)
    
    # 建立時間 (自動填入伺服器當下時間)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AnalysisLog(id={self.id}, stock={self.stock_id}, date={self.created_at})>"