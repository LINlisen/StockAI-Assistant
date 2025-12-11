# backend/services/ai_service.py
import google.generativeai as genai
import json
import requests

class AIService:
    PROMPT_TEMPLATES = {
        "standard": """
        你是一位資深台股操盤手，並且能夠提供明確且果斷的判斷。
        風格：綜合技術面與籌碼面，給出最客觀的操作建議。
        """,

        "balanced": """
        你是一個「平衡型」的量化交易員。
        策略重點：尋找趨勢確認的進場點，重視風險報酬比。
        進場條件：均線多頭排列且回測支撐不破，或指標出現明確黃金交叉。
        風險控管：停損設在關鍵支撐下方 2-3%。
        """,
        
        "aggressive": """
        你是一個「激進型」的動能交易員 (Momentum Trader)。
        策略重點：追逐強勢股，只要有突破訊號就勇敢進場。
        進場條件：爆量長紅、突破區間、RSI 強勢區鈍化。
        風險控管：停損設在 5% 左右，願意承擔較大波動以換取飆漲段。
        心態：寧可追高被套，不可錯過飆股。
        """,
        
        "conservative": """
        你是一個「極度保守」的價值投資與波段交易員。
        策略重點：只在勝率極高時出手，寧可錯過也不要虧損。
        進場條件：股價跌深至長期均線(年線)有撐，或乖離率過大出現超賣訊號(RSI < 20)。
        風險控管：嚴格停損，只要跌破支撐立刻出場。
        心態：保本第一，獲利第二。
        """
    }

    def __init__(self):
        pass

    def get_available_models(self, api_key: str) -> list:
       """
       列出該 API Key 可用的所有生成式模型
       """
       try:
           genai.configure(api_key=api_key)
           model_list = []
           for m in genai.list_models():
               # 只列出支援 'generateContent' (文字生成) 的模型
               if 'generateContent' in m.supported_generation_methods:
                   model_list.append(m.name)
           
           # 排序一下，比較好找
           return sorted(model_list)
       except Exception as e:
           # 如果 API Key 錯誤或連線失敗，回傳空陣列或預設值
           print(f"Fetch models error: {e}")
           return []

    def get_analysis(self, api_key: str, stock_id: str, stock_name: str, mode: str, cost: float, context_data: str, provider: str = "gemini", model_name: str = "gemini-1.5-flash", ollama_url: str = None, prompt_style: str = "standard"):
        """
        呼叫 AI 進行操盤分析 (回傳文字報告)
        """
        try:
            # 1. 取得對應的人格設定 (若找不到則預設用 standard)
            persona = self.PROMPT_TEMPLATES.get(prompt_style, self.PROMPT_TEMPLATES["standard"])

            if(mode == "long"):
                mode = "做多"
            elif(mode == "short"):
                mode = "做空"

            # 2. 組合完整的 Prompt (人格 + 數據 + 任務)
            prompt = f"""
            {persona}

            請分析以下股票數據。
            參數: 代號 {stock_id}, 股票名稱 {stock_name} 方向 {mode}, 成本 {cost}
            數據: {context_data}
            
            任務:
            1. 給出明確操作建議 (買進/賣出/續抱/止損)。
            2. 指出關鍵支撐與壓力價位。
            3. 使用條列式，口語化，500字內。
            4. 是否適合作為隔日沖的標的。
            5. 根據分析結果給出 (1) 進場價格 (2) 停利價格 (3) 停損價格
            6. 根據近20日的資料給出壓力價位、支撐價位、爆大量日期，請務必在文章結尾附上以下 JSON 格式的關鍵數據（不要放在程式碼區塊中）：
            {{ "resistancePrice": "數值", "supportPrice": "數值", "volumeSpikeDate": "YYYY/MM/DD" }}
            
            ⚠️ 重要：請直接輸出純文字報告，不要使用 JSON 格式。
            """


            if provider == "ollama":
            # 呼叫 Ollama，json_mode=False (我們要文字報告)
                return self._call_ollama(model_name, prompt, ollama_url, json_mode=False)
            else:
                # 呼叫 Gemini
                if not api_key:
                    return "⚠️ 請輸入 Gemini API Key"
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    return response.text
                except Exception as e:
                    return f"Gemini Error: {e}"
            
        except Exception as e:
            return f"AI 分析失敗: {str(e)}"
        
    def get_trade_signal(self, api_key: str, stock_id: str, context_data: str, provider: str = "gemini", model_name: str = "gemini-1.5-flash", ollama_url: str = None, prompt_style: str = "balanced"):
        # 1. 根據風格取得對應的 Persona 設定
        # 如果找不到對應風格，就用預設 balanced
        persona = self.PROMPT_TEMPLATES.get(prompt_style, self.PROMPT_TEMPLATES["balanced"])

        # 2. 組合最終 System Prompt
        system_prompt = f"""
        {persona}
        
        請根據提供的股票數據進行分析。
        股票代號: {stock_id}
        數據摘要: {context_data}

        任務：
        1. 判斷是否適合進場（做多 Long 或 觀望 Hold）。
        2. 如果做多，給出明確的進場價、停損價、停利價。
        3. 嚴格輸出 JSON 格式，不要包含 Markdown 標記。

        JSON 格式範例：
        {{
            "action": "BUY", 
            "entry_price": 100.5,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "reason": "依據激進策略，突破前高進場"
        }}
        """

        if provider == "ollama":
            return self._call_ollama(model_name, system_prompt, ollama_url, json_mode=True)
        else:
            return self._call_gemini(api_key, model_name, system_prompt)


    def _call_gemini(self, api_key, model_name, prompt):
        try:
            if not api_key:
                return {"action": "HOLD", "reason": "未提供 Gemini API Key"}
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            # 加上 JSON mode 提示比較保險
            response = model.generate_content(prompt + "\n請確保只回傳 JSON 字串。")
            text = response.text.strip()
            
            # 清理 markdown
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text)
        except Exception as e:
            print(f"Gemini Error: {e}")
            return {"action": "HOLD", "reason": f"Gemini 錯誤: {str(e)}"}

    def _call_ollama(self, model_name, prompt, custom_url=None, json_mode=False):
        """
        呼叫本地 Ollama API
        """
        try:
            # 如果有傳入 custom_url (Ngrok網址)，就用它；否則用 localhost
            base_url = custom_url if custom_url else "http://localhost:11434"
            # 確保網址結尾沒有斜線，避免變成 //api/chat
            base_url = base_url.rstrip("/")
            
            url = f"{base_url}/api/chat"
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "num_predict": 2048,  # 強制讓它最多可以生成 2048 個 token (避免話講一半被切掉)
                    "temperature": 0.7,   # 0.7 比較有創意，0.1 比較死板
                    "top_p": 0.9
                }
            }
            
            # 只有在回測功能 (json_mode=True) 時才強制 JSON
            if json_mode:
                payload["format"] = "json"
            
            # 設定 timeout，避免等太久
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "{}")
                if json_mode:
                    return json.loads(content)
                else:
                    return content # 直接回傳文字
            else:
                return {"action": "HOLD", "reason": f"Ollama HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"Ollama Error: {e}")
            return {"action": "HOLD", "reason": "Ollama 連線失敗或逾時"}