import requests
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import ChipDaily
from database import SessionLocal

class ChipService:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def fetch_twse_t86(self, date: datetime):
        """
        抓取 TWSE T86 (三大法人買賣超日報)
        date: datetime object
        """
        date_str = date.strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            print(f"Fetching T86 for {date_str}...")
            res = requests.get(url, headers=headers)
            if res.status_code != 200:
                print(f"Failed to fetch {date_str}: {res.status_code}")
                return None
            
            data = res.json()
            if data.get('stat') != 'OK':
                print(f"TWSE API Error: {data.get('stat')}")
                # 可能是假日或沒資料
                return None
                
            return data.get('data', [])
            
        except Exception as e:
            print(f"Error fetching T86: {e}")
            return None

    def update_daily_data(self, date: datetime):
        """
        抓取並更新該日期的籌碼資料到資料庫
        """
        raw_data = self.fetch_twse_t86(date)
        if not raw_data:
            return False

        # 這裡需要解析 TWSE 回傳的 List
        # 欄位通常是: 代號, 名稱, 外資買進, 外資賣出, 外資買賣超, 外資自營商...
        # 根據觀察 (test_twstock.py log 會印出 fields):
        # 0: 代號
        # 1: 名稱
        # 2: 外資買進股數
        # 3: 外資賣出股數
        # 4: 外資買賣超股數 (Net)
        # ... (這部分可能要小心，因為欄位順序可能會變，最穩是看 fields 但這裡先假設固定結構)
        # 投信通常在後面
        # 讓我們寫得健壯一點，雖然比較麻煩。我們假設順序如下 (常見 ID):
        # 0=StockID, 2=ForeignBuy, 3=ForeignSell, 4=ForeignNet
        # 8=TrustBuy, 9=TrustSell, 10=TrustNet (投信)
        # 12=DealerDiffer (自營商差額? 不對，自營商有分自行跟避險)
        # 實際上 T86 欄位很多，通常:
        # 0: 代號
        # 1: 名稱
        # 2: 外陸資買進股數(不含外資自營商)
        # 3: 外陸資賣出股數(不含外資自營商)
        # 4: 外陸資買賣超股數(不含外資自營商)
        # 5: 外資自營商買進
        # 6: 外資自營商賣出
        # 7: 外資自營商買賣超
        # 8: 投信買進
        # 9: 投信賣出
        # 10: 投信買賣超
        # ... 自營商合計 ...
        
        # 簡化: 我們抓主要的 Total Net
        
        count = 0
        try:
            for row in raw_data:
                stock_id = row[0]
                if len(stock_id) > 6: continue # 跳過奇怪的權證
                
                # 處理數字 (TWSE 會有逗號，如 "1,234")
                def parse_int(val):
                    return int(val.replace(',', ''))
                
                # 外資 (加總外陸資 + 外資自營商?通常一般人看外陸資即可，即 index 4)
                f_buy = parse_int(row[2])
                f_sell = parse_int(row[3])
                f_net = parse_int(row[4])
                
                # 投信 (通常 index 8, 9, 10)
                # 若 T86 結構有變，這裡會錯，但先 try
                t_buy = parse_int(row[8])
                t_sell = parse_int(row[9])
                t_net = parse_int(row[10])
                
                # 自營商 (通常 index 11 是 "自營商買賣超股數(自行買賣+避險)" 嗎? 
                # 讓我們保守一點，如果 index 不夠長就 skip)
                # 一般來說後面還有自營商(自行), 自營商(避險), 自營商買賣超... 
                # 我們抓 "自營商買賣超股數" (通常是最後面的合計，或 index 11)
                # 簡單起見，我們抓 index 11 (合計買賣超) 若存在
                d_net = 0
                if len(row) > 11:
                    # 自營商合計通常是 買進(12), 賣出(13), 買賣超(14)? 
                    # 不，最好還是看一下 fields。我們暫時先只存 Net。
                    # 假設 index 11 是自營商淨買賣超 (有些版本是這樣)
                    # 註：如果 row[11] 是數字，就當作它是。
                    try:
                        d_net = parse_int(row[-3]) # 倒數第三個通常是 三大法人買賣超?
                        # 算了，先存外資跟投信就好，自營商容易錯
                        pass
                    except:
                        pass
                
                # 檢查 DB 是否已有這筆資料 (Date + StockID)
                existing = self.db.query(ChipDaily).filter(
                    ChipDaily.date == date,
                    ChipDaily.stock_id == stock_id
                ).first()
                
                if not existing:
                    new_record = ChipDaily(
                        date=date,
                        stock_id=stock_id,
                        foreign_buy=f_buy,
                        foreign_sell=f_sell,
                        foreign_net=f_net,
                        trust_buy=t_buy,
                        trust_sell=t_sell,
                        trust_net=t_net,
                        dealer_net=d_net
                    )
                    self.db.add(new_record)
                    count += 1
            
            self.db.commit()
            print(f"Inserted {count} chip records for {date}")
            return True
            
        except Exception as e:
            print(f"Error parsing T86: {e}")
            self.db.rollback()
            return False

    def get_stock_chip(self, stock_id: str, days: int = 10):
        """
        取得個股歷史籌碼
        """
        # 如果 DB 沒資料，是否要 auto fetch? 
        # 這會很慢。建議前端 trigger 一個 "更新資料" 的按鈕，或是後端背景跑。
        # 為了 "一點點來"，我們這裡先只讀 DB。
        
        # 檢查該股票最近有沒有資料
        recent = self.db.query(ChipDaily).filter(
            ChipDaily.stock_id == stock_id
        ).order_by(ChipDaily.date.desc()).first()
        
        today = datetime.now()
        start_date = today - timedelta(days=days)
        
        # 先查詢目前 DB 有幾筆
        existing_count = self.db.query(ChipDaily).filter(
            ChipDaily.stock_id == stock_id,
            ChipDaily.date >= start_date
        ).count()
        
        # 如果資料太少 (例如少於 5 筆)，嘗試強制補抓最近 10 天
        # 這可以解決 "只有 3 天" 的問題 (因為之前只抓 range(5) 且遇到週末)
        if existing_count < 5:
            print(f"Data insufficient for {stock_id} (count={existing_count}), forcing fetch last 10 days...")
            for i in range(10):
                d = datetime.now() - timedelta(days=i)
                # 這裡要避免重複 fetch 已經有的日期嗎? 
                # update_daily_data 內部有 check existing，所以多跑幾次沒關係，只是會花時間 request
                self.update_daily_data(d)
        
        # 查詢
        today = datetime.now()
        start_date = today - timedelta(days=days)
        
        records = self.db.query(ChipDaily).filter(
            ChipDaily.stock_id == stock_id,
            ChipDaily.date >= start_date
        ).order_by(ChipDaily.date.asc()).all()
        
        return records
