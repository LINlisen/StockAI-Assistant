# backend/services/ai_service.py
import google.generativeai as genai
import json
import requests

class AIService:
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

    def get_analysis(self, api_key: str, stock_id: str, mode: str, cost: float, context_data: str, model_name: str):
        """
        呼叫 Gemini API 進行分析
        """
        try:
            genai.configure(api_key=api_key)
            
            # 自動選擇模型邏輯
            model = genai.GenerativeModel(model_name)
            
            # 如果要更嚴謹可以加入原本的 find_best_model 邏輯，這裡簡化直接指定
            model = genai.GenerativeModel(model_name)

            prompt = f"""
            你是一位資深台股操盤手，並且能夠提供明確且果斷的判斷。請分析以下股票數據。
            參數: 代號 {stock_id}, 方向 {mode}, 成本 {cost}
            數據: {context_data}
            
            任務:
            1. 給出明確操作建議 (買進/賣出/續抱/止損)。
            2. 指出關鍵支撐與壓力價位。
            3. 使用條列式，口語化，500字內。
            4. 是否適合作為隔日沖的標的。
            5. 根據分析結果給出 (1) 進場價格 (2) 停利價格 (3) 停損價格
            """
            
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"AI 分析失敗: {str(e)}"
        
    def get_trade_signal(self, api_key: str, stock_id: str, context_data: str, provider: str = "gemini", model_name: str = "gemini-1.5-flash"):
        """
        根據 provider 決定呼叫 Gemini 還是 Ollama
        """
        # 定義 Prompt (共用)
        system_prompt = f"""
        你是一個量化交易決策系統。請根據提供的股票數據進行分析。
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
            "reason": "突破均線糾結"
        }}
        """

        if provider == "ollama":
            return self._call_ollama(model_name, system_prompt)
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

    def _call_ollama(self, model_name, prompt):
        """
        呼叫本地 Ollama API (預設 port 11434)
        """
        try:
            url = "http://localhost:11434/api/chat"
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "format": "json" # Ollama 支援強制 JSON 模式 (需較新版本)
            }
            
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "{}")
                print(f"🤖 AI Raw Response: {content}") 
                return json.loads(content)
            else:
                return {"action": "HOLD", "reason": f"Ollama HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"Ollama Error: {e}")
            return {"action": "HOLD", "reason": "Ollama 連線失敗，請確認是否已啟動 (ollama serve)"}