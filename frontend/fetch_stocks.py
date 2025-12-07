"""
台灣證券交易所股票代號爬蟲
從 TWSE API 抓取所有上市、上櫃、興櫃股票資料並更新 stock_mapping.py
"""

import requests
from bs4 import BeautifulSoup
import re

def fetch_stock_data(url, market_type):
    """
    從 TWSE API 抓取股票資料
    
    Args:
        url: API URL
        market_type: 市場類型 (上市/上櫃/興櫃)
    
    Returns:
        dict: {股票代號: 股票名稱}
    """
    print(f"正在抓取 {market_type} 股票資料...")
    
    try:
        response = requests.get(url, timeout=30)
        response.encoding = 'big5'  # TWSE 使用 Big5 編碼
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 找到所有的表格行
        rows = soup.find_all('tr')
        
        stock_dict = {}
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:  # 確保有足夠的欄位
                # 第一欄通常是 "股票代號 股票名稱"
                first_col = cols[0].text.strip()
                
                # 使用正則表達式分離代號和名稱
                # 格式通常是: "2330　台積電" 或 "2330 台積電"
                match = re.match(r'(\d{4})\s+(.+)', first_col)
                
                if match:
                    stock_code = match.group(1)
                    stock_name = match.group(2).strip()
                    
                    # 過濾掉特殊股票 (如 ETF、權證等)
                    # 只保留普通股票
                    if len(stock_code) == 4 and stock_code.isdigit():
                        # 移除股票名稱中的特殊符號
                        stock_name = stock_name.replace('*', '').strip()
                        stock_dict[stock_code] = stock_name
        
        print(f"✓ {market_type} 抓取完成，共 {len(stock_dict)} 檔股票")
        return stock_dict
        
    except Exception as e:
        print(f"✗ 抓取 {market_type} 失敗: {e}")
        return {}

def main():
    """主程式"""
    
    urls = [
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", "上市證券"),
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", "上櫃證券"),
        ("https://isin.twse.com.tw/isin/C_public.jsp?strMode=5", "興櫃證券")
    ]
    
    all_stocks = {}
    
    # 抓取所有市場的股票
    for url, market_type in urls:
        stocks = fetch_stock_data(url, market_type)
        all_stocks.update(stocks)
    
    print(f"\n總計抓取到 {len(all_stocks)} 檔股票")
    
    # 按代號排序
    sorted_stocks = dict(sorted(all_stocks.items()))
    
    # 生成 Python 字典格式的程式碼
    print("\n正在生成 stock_mapping.py 內容...")
    
    output_lines = [
        "# Taiwan Stock Symbol to Name Mapping",
        "# 台股代號對應表",
        "# 資料來源: 台灣證券交易所 (TWSE)",
        f"# 更新時間: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "STOCK_MAPPING = {"
    ]
    
    # 分類整理
    listed_stocks = {}  # 上市 (1xxx-2xxx)
    otc_stocks = {}     # 上櫃 (3xxx-8xxx)
    emerging_stocks = {} # 興櫃 (其他)
    
    for code, name in sorted_stocks.items():
        first_digit = code[0]
        if first_digit in ['1', '2']:
            listed_stocks[code] = name
        elif first_digit in ['3', '4', '5', '6', '7', '8']:
            otc_stocks[code] = name
        else:
            emerging_stocks[code] = name
    
    # 上市股票
    if listed_stocks:
        output_lines.append("    # === 上市股票 (Listed Stocks) ===")
        for code, name in listed_stocks.items():
            output_lines.append(f'    "{code}": "{name}",')
    
    # 上櫃股票
    if otc_stocks:
        output_lines.append("")
        output_lines.append("    # === 上櫃股票 (OTC Stocks) ===")
        for code, name in otc_stocks.items():
            output_lines.append(f'    "{code}": "{name}",')
    
    # 興櫃股票
    if emerging_stocks:
        output_lines.append("")
        output_lines.append("    # === 興櫃股票 (Emerging Stocks) ===")
        for code, name in emerging_stocks.items():
            output_lines.append(f'    "{code}": "{name}",')
    
    output_lines.append("}")
    output_lines.append("")
    output_lines.append("# 建立反向對應表 (名稱 -> 代號)")
    output_lines.append("NAME_TO_SYMBOL = {name: symbol for symbol, name in STOCK_MAPPING.items()}")
    output_lines.append("")
    output_lines.append('def get_stock_name(stock_id: str) -> str:')
    output_lines.append('    """')
    output_lines.append('    根據股票代號取得股票名稱')
    output_lines.append('    ')
    output_lines.append('    Args:')
    output_lines.append('        stock_id: 股票代號 (例如: "2330")')
    output_lines.append('        ')
    output_lines.append('    Returns:')
    output_lines.append('        股票名稱，如果找不到則返回空字串')
    output_lines.append('    """')
    output_lines.append('    return STOCK_MAPPING.get(stock_id, "")')
    output_lines.append('')
    output_lines.append('def get_stock_symbol(stock_name: str) -> str:')
    output_lines.append('    """')
    output_lines.append('    根據股票名稱取得股票代號')
    output_lines.append('    ')
    output_lines.append('    Args:')
    output_lines.append('        stock_name: 股票名稱 (例如: "台積電")')
    output_lines.append('        ')
    output_lines.append('    Returns:')
    output_lines.append('        股票代號，如果找不到則返回空字串')
    output_lines.append('    """')
    output_lines.append('    return NAME_TO_SYMBOL.get(stock_name, "")')
    output_lines.append('')
    output_lines.append('def get_stock_display_name(stock_id: str) -> str:')
    output_lines.append('    """')
    output_lines.append('    取得股票的完整顯示名稱 (代號 + 名稱)')
    output_lines.append('    ')
    output_lines.append('    Args:')
    output_lines.append('        stock_id: 股票代號 (例如: "2330")')
    output_lines.append('        ')
    output_lines.append('    Returns:')
    output_lines.append('        完整顯示名稱 (例如: "2330 台積電")')
    output_lines.append('    """')
    output_lines.append('    name = STOCK_MAPPING.get(stock_id)')
    output_lines.append('    if name:')
    output_lines.append('        return f"{stock_id} {name}"')
    output_lines.append('    return stock_id')
    output_lines.append('')
    output_lines.append('def search_stock(query: str) -> list:')
    output_lines.append('    """')
    output_lines.append('    搜尋股票 (支援代號或名稱的部分匹配)')
    output_lines.append('    ')
    output_lines.append('    Args:')
    output_lines.append('        query: 搜尋關鍵字')
    output_lines.append('        ')
    output_lines.append('    Returns:')
    output_lines.append('        符合的股票列表 [(代號, 名稱), ...]')
    output_lines.append('    """')
    output_lines.append('    query = query.strip()')
    output_lines.append('    if not query:')
    output_lines.append('        return []')
    output_lines.append('    ')
    output_lines.append('    results = []')
    output_lines.append('    ')
    output_lines.append('    # 搜尋代號')
    output_lines.append('    for symbol, name in STOCK_MAPPING.items():')
    output_lines.append('        if query in symbol or query in name:')
    output_lines.append('            results.append((symbol, name))')
    output_lines.append('    ')
    output_lines.append('    return results[:20]  # 限制最多20筆結果')
    output_lines.append('')
    output_lines.append('def get_all_stocks() -> list:')
    output_lines.append('    """')
    output_lines.append('    取得所有股票列表')
    output_lines.append('    ')
    output_lines.append('    Returns:')
    output_lines.append('        所有股票列表 [(代號, 名稱), ...]，按代號排序')
    output_lines.append('    """')
    output_lines.append('    return sorted([(symbol, name) for symbol, name in STOCK_MAPPING.items()])')
    
    # 寫入檔案
    output_file = "stock_mapping_new.py"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"✓ 已生成新的股票對應表: {output_file}")
    print(f"\n統計資訊:")
    print(f"  - 上市股票: {len(listed_stocks)} 檔")
    print(f"  - 上櫃股票: {len(otc_stocks)} 檔")
    print(f"  - 興櫃股票: {len(emerging_stocks)} 檔")
    print(f"  - 總計: {len(all_stocks)} 檔")
    print(f"\n請檢查 {output_file} 後，手動替換 stock_mapping.py")

if __name__ == "__main__":
    main()
