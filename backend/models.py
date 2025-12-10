from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# --- 新增 User 模型 ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String, unique=True, index=True)  # 帳號 (唯一)
    username = Column(String)                          # 使用者名稱
    password_hash = Column(String)                     # SHA256 加密後的密碼
    api_token = Column(String, nullable=True)          # Gemini API Key (選填)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    logs = relationship("AnalysisLog", back_populates="owner")

class AnalysisLog(Base):
    """
    分析紀錄表 (analysis_logs)
    用來儲存每一次 AI 分析的結果，方便日後回測或查詢歷史紀錄。
    """
    __tablename__ = "analysis_logs"

    # 主鍵 ID，自動遞增
    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id")) 
    
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

    # 建立關聯
    owner = relationship("User", back_populates="logs")

    def __repr__(self):
        return f"<AnalysisLog(id={self.id}, stock={self.stock_id}, date={self.created_at})>"
    
class BacktestRecord(Base):
    __tablename__ = "backtest_records"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(String, index=True)
    strategy_name = Column(String)  # 例如 "AI_Gemini_Flash"
    initial_capital = Column(Float)
    
    # 儲存完整的統計結果 (JSON 轉字串存入)
    # 包含: final_balance, total_return, trades_list, equity_curve
    result_data = Column(Text) 
    
    # 建立時間 (用來判斷快取是否過期，例如超過 1 天就重跑)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChipDaily(Base):
    """
    籌碼日報表 (chip_daily)
    儲存每日個股的三大法人買賣超數據
    資料來源: TWSE T86
    """
    __tablename__ = "chip_daily"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)         # 日期 (YYYY-MM-DD)
    stock_id = Column(String(10), index=True)   # 股票代號 (2330)
    
    # 外資 (Foreign Investors)
    foreign_buy = Column(Float, default=0)      # 買進股數
    foreign_sell = Column(Float, default=0)     # 賣出股數
    foreign_net = Column(Float, default=0)      # 買賣超股數 (Net)
    
    # 投信 (Investment Trust)
    trust_buy = Column(Float, default=0)
    trust_sell = Column(Float, default=0)
    trust_net = Column(Float, default=0)
    
    # 自營商 (Dealer) - 包含自行買賣與避險
    dealer_buy = Column(Float, default=0)
    dealer_sell = Column(Float, default=0)
    dealer_net = Column(Float, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())