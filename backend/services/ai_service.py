# backend/services/ai_service.py
import google.generativeai as genai

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
            你是一位資深台股操盤手。請分析以下股票數據。
            參數: 代號 {stock_id}, 方向 {mode}, 成本 {cost}
            數據: {context_data}
            
            任務:
            1. 給出明確操作建議 (買進/賣出/續抱/止損)。
            2. 指出關鍵支撐與壓力價位。
            3. 使用條列式，口語化，400字內。
            4. 給出明確的價位操作，是否適合作為隔日沖的標的。
            """
            
            response = model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            return f"AI 分析失敗: {str(e)}"