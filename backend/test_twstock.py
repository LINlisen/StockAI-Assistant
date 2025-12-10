import requests
import json
import time
import pandas as pd

def test_twse_direct():
    print("Testing direct connection to TWSE for Institutional Investors data...")
    # URL for "Daily Trading Details of Foreign and Institutional Investors"
    # T86: 三大法人買賣超日報
    # date format: YYYYMMDD
    url = "https://www.twse.com.tw/rwd/zh/fund/T86?date=20241206&selectType=ALLBUT0999&response=json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code == 200:
            data = res.json()
            if data.get('stat') == 'OK':
                print("Successfully fetched data!")
                # Parse one entry to show structure
                fields = data.get('fields')
                print(f"Fields: {fields}")
                
                # Check for 2330
                for row in data.get('data', []):
                    if row[0] == '2330':
                        print(f"Found 2330: {row}")
                        break
            else:
                print(f"API returned error: {data.get('stat')}")
        else:
            print("Failed to connect.")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_twse_direct()
