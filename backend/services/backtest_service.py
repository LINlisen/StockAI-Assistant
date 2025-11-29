# backend/services/backtest_service.py
import json
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from services.stock_service import StockService
from services.ai_service import AIService

class BacktestService:
    def __init__(self):
        self.stock_service = StockService()
        self.ai_service = AIService()

    def get_cached_result(self, db: Session, stock_id: str, capital: float, strategy_name: str):
        """
        檢查是否有 24 小時內的有效快取
        """
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        record = db.query(models.BacktestRecord).filter(
            models.BacktestRecord.stock_id == stock_id,
            models.BacktestRecord.initial_capital == capital,
            models.BacktestRecord.strategy_name == strategy_name,
            models.BacktestRecord.created_at >= one_day_ago
        ).order_by(models.BacktestRecord.created_at.desc()).first()
        
        if record:
            return json.loads(record.result_data)
        return None

    def save_result(self, db: Session, stock_id: str, capital: float, result: dict, strategy_name: str):
        """
        將結果存入資料庫
        """
        db_record = models.BacktestRecord(
            stock_id=stock_id,
            strategy_name=strategy_name,
            initial_capital=capital,
            result_data=json.dumps(result) # 轉成 JSON 字串
        )
        db.add(db_record)
        db.commit()

    def calculate_cost(self, price: float, shares: int, is_buy: bool) -> float:
        """
        計算交易成本 (含手續費與稅)
        """
        fee_rate = 0.001425
        tax_rate = 0.003
        
        amount = price * shares
        # 手續費最低 20 元 (這裡簡化，先不設低消)
        fee = int(amount * fee_rate)
        
        if is_buy:
            return amount + fee
        else:
            tax = int(amount * tax_rate)
            return amount - fee - tax

    # 修改 run_backtest 簽章，接收 provider 和 model_name
    def run_backtest(self, db: Session, api_key: str, stock_id: str, initial_capital: float, provider: str, model_name: str):
        
        # 組合出唯一的策略名稱，例如 "Backtest_ollama_llama3" 或 "Backtest_gemini_gemini-1.5-flash"
        strategy_key = f"Backtest_{provider}_{model_name}"

        # 1. 檢查快取 (傳入新的 key)
        cached = self.get_cached_result(db, stock_id, initial_capital, strategy_key)
        if cached:
            return cached

        # 2. 抓取數據 (回測最近 1 年)
        df_raw = self.stock_service.fetch_data(stock_id)
        
        # 🔥🔥🔥 修正重點：加上這行來計算技術指標 (MA, KD, ...) 🔥🔥🔥
        df = self.stock_service.calculate_indicators(df_raw)

        # 確保數據夠多，至少要有 100 天來跑指標
        if len(df) < 100:
            return {"error": "資料不足，無法回測"}

        balance = initial_capital
        position = None       # 持倉狀態: None 或 dict
        pending_order = None  # 掛單狀態: None 或 {price, expiry, reason, sl, tp}
        
        trades = []           # 交易紀錄
        equity_curve = []     # 資產曲線
        
        # 為了節省 Token，設定冷卻時間 (若 AI 說觀望，N 天內不問)
        ai_cooldown = 0 

        # 從第 60 天開始跑 (前面留給 MA 計算)
        for i in range(60, len(df) - 1):
            curr_date = df.index[i]
            curr_row = df.iloc[i]
            next_row = df.iloc[i+1] # 用來模擬隔天成交
            
            # 每日資產快照 (現金 + 持倉市值)
            current_equity = balance
            if position:
                current_equity += (position['shares'] * curr_row['Close'])
            equity_curve.append({"date": str(curr_date.date()), "equity": current_equity})

            # --- 狀態 1: 持倉中 (檢查停損停利) ---
            if position:
                # 檢查隔天是否觸發出場
                exit_price = None
                exit_reason = ""

                # 優先檢查停損 (假設盤中先碰到低點)
                if next_row['Low'] <= position['stop_loss']:
                    exit_price = min(next_row['Open'], position['stop_loss'])
                    exit_reason = "停損出場"
                
                # 再檢查停利
                elif next_row['High'] >= position['take_profit']:
                    exit_price = max(next_row['Open'], position['take_profit'])
                    exit_reason = "停利出場"
                
                # 執行出場
                if exit_price:
                    revenue = self.calculate_cost(exit_price, position['shares'], is_buy=False)
                    balance += revenue
                    profit = revenue - position['cost_basis']
                    profit_pct = (profit / position['cost_basis']) * 100
                    
                    trades.append({
                        "entry_date": position['entry_date'],
                        "exit_date": str(next_row.name.date()),
                        "stock_id": stock_id,
                        "type": "Long",
                        "entry_price": position['entry_price'],
                        "exit_price": exit_price,
                        "shares": position['shares'],
                        "profit": int(profit),
                        "profit_pct": round(profit_pct, 2),
                        "reason": exit_reason
                    })
                    position = None # 恢復空手
                    ai_cooldown = 0 # 剛賣出，可以馬上再問 AI

            # --- 狀態 2: 有掛單 (檢查是否成交或過期) ---
            elif pending_order:
                # 1. 檢查過期
                pending_order['expiry'] -= 1
                if pending_order['expiry'] <= 0:
                    # 訂單過期，取消
                    pending_order = None
                    ai_cooldown = 0 # 重新分析
                    continue
                
                # 2. 檢查是否成交 (隔天最低價 < 掛單價)
                if next_row['Low'] <= pending_order['entry_price']:
                    # 成交！
                    # 如果開盤就低於掛單價，以開盤價成交 (買更便宜)
                    real_entry_price = min(next_row['Open'], pending_order['entry_price'])
                    
                    # 計算可買股數 (簡單全倉，或固定比例)
                    # 預留 2% 現金付手續費
                    max_amount = balance * 0.98 
                    shares = int(max_amount / real_entry_price)
                    
                    if shares > 0:
                        cost_basis = self.calculate_cost(real_entry_price, shares, is_buy=True)
                        if balance >= cost_basis:
                            balance -= cost_basis
                            position = {
                                "entry_date": str(next_row.name.date()),
                                "entry_price": real_entry_price,
                                "shares": shares,
                                "cost_basis": cost_basis,
                                "stop_loss": pending_order['sl'],
                                "take_profit": pending_order['tp']
                            }
                            # 成交後清除掛單
                            pending_order = None 

            # --- 狀態 3: 空手且無掛單 (詢問 AI) ---
            else:
                if ai_cooldown > 0:
                    ai_cooldown -= 1
                else:
                    # 準備數據給 AI
                    subset_df = df.iloc[:i+1] # 只看過去
                    summary = self.stock_service.get_technical_summary(subset_df)
                    
                    # 呼叫 AI (這裡假設 ai_service 已經有 get_trade_signal 方法)
                    try:
                        signal = self.ai_service.get_trade_signal(api_key, stock_id, summary['context_str'], provider=provider, model_name=model_name)
                        
                        if signal.get('action') == "BUY":
                            # AI 建議買進 -> 建立掛單
                            pending_order = {
                                "entry_price": signal['entry_price'],
                                "sl": signal['stop_loss'],
                                "tp": signal['take_profit'],
                                "expiry": 5, # 訂單有效期 5 天
                                "reason": signal.get('reason', 'AI Signal')
                            }
                        else:
                            # AI 說 HOLD -> 冷卻 3 天別吵它
                            ai_cooldown = 3
                            
                    except Exception as e:
                        print(f"AI Call Error: {e}")
                        ai_cooldown = 3

        # 整理最終結果
        final_equity = balance
        if position: # 如果最後一天還持倉，以收盤價計算市值
            # 這裡簡化不扣賣出手續費，僅算市值
            final_equity += (position['shares'] * df.iloc[-1]['Close'])

        result = {
            "stock_id": stock_id,
            "initial_capital": initial_capital,
            "final_equity": int(final_equity),
            "total_return_pct": round(((final_equity - initial_capital) / initial_capital) * 100, 2),
            "trade_count": len(trades),
            "trades": trades,
            "equity_curve": equity_curve
        }

        # 3. 寫入快取
        self.save_result(db, stock_id, initial_capital, result, strategy_key)
        
        return result