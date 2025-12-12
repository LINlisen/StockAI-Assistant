# backend/services/report_service.py
import os
from sqlalchemy.orm import Session
from sqlalchemy import desc
from services.stock_service import StockService
from services.ai_service import AIService
import models, schemas
import json
import re

# PDF 相關
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
class ReportService:
    def __init__(self):
        self.stock_service = StockService()
        self.ai_service = AIService()

    def _parse_strategy_style(self, strategy_name: str):
        try:
            clean = strategy_name.replace("Backtest_", "")
            parts = clean.split("_")
            return parts[-1]
        except:
            return "aggressive"

    def format_ai_text(self, text):
        """
        格式化 AI 文字：
        1. 移除 Emoji
        2. 將 Markdown **粗體** 轉為 ReportLab <b >標籤
        3. 將 \n 換行轉為 <br/>
        """
        if not text: return ""
        
        text = str(text)
        
        # 1. 移除 Emoji (Unicode 範圍)
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        
        # 2. 處理 Markdown 粗體 (**text**) -> <b>text</b>
        # 使用正則表達式非貪婪匹配
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # 3. 處理標題符號 (例如 ### 標題) -> 改為粗體並換行
        text = re.sub(r'#+\s*(.*)', r'<b>\1</b><br/>', text)

        # 4. 將換行符號 \n 轉為 <br/> (這是 PDF 換行的關鍵)
        text = text.replace('\n', '<br/>')
        
        return text
    
    def generate_pdf(self, filename: str, report_data: list):
        """
        使用 Platypus 引擎製作支援排版的 PDF
        """
        # 1. 註冊中文字型
        font_path = "font.ttf" 
        font_name = 'Helvetica' # 預設 fallback
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
            font_name = 'ChineseFont'
        else:
            print("⚠️ 警告：找不到 font.ttf，中文將無法顯示")

        # 2. 設定文件模板
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )

        # 3. 定義樣式 (Styles)
        styles = getSampleStyleSheet()
        
        # 定義中文普通樣式
        style_normal = ParagraphStyle(
            name='ChineseNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14, # 行高
            spaceAfter=6, # 段落後留白
            alignment=TA_LEFT,
            wordWrap='CJK' # 支援中文自動換行
        )

        # 定義中文標題樣式
        style_heading = ParagraphStyle(
            name='ChineseHeading',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=16,
            leading=20,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # 定義 AI 模型標題樣式
        style_subheading = ParagraphStyle(
            name='ChineseSubHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=12,
            leading=16,
            spaceAfter=6,
            textColor=colors.darkred
        )

        # 4. 建立內容 (Story)
        story = []

        # -- 文件標題 --
        story.append(Paragraph("<b>AI 智能選股分析報告</b>", style_heading))
        story.append(Paragraph("本報告由 AI 自動生成，僅供參考，不代表投資建議。", style_normal))
        story.append(Spacer(1, 12)) # 空行

        # -- 遍歷每檔股票 --
        for stock_report in report_data:
            # 股票標題 (例如：【2330 台積電】)
            s_id = str(stock_report.get('stock_id', ''))
            s_name = str(stock_report.get('stock_name', ''))
            s_price = str(stock_report.get('price', 0))
            
            title_text = f"【{s_id} {s_name}】 - 收盤價: {s_price}"
            story.append(Paragraph(title_text, style_heading))
            
            # 技術指標摘要
            strategies = stock_report.get('matched_strategies', [])
            if not isinstance(strategies, list): strategies = [str(strategies)]
            strats_text = ", ".join(strategies)
            trend_text = str(stock_report.get('trend', 'N/A'))
            
            info_text = f"<b>趨勢:</b> {trend_text} | <b>觸發策略:</b> {strats_text}"
            story.append(Paragraph(info_text, style_normal))
            story.append(Spacer(1, 8))

            # AI 分析內容
            for analysis in stock_report.get('analyses', []):
                model_name = str(analysis.get('model', 'Unknown'))
                style_name = str(analysis.get('style', 'Unknown'))
                ret_val = str(analysis.get('return', 0))
                
                # 子標題：模型資訊
                header_text = f"[{model_name} / {style_name}] 分析結果 (回測報酬: {ret_val}%)"
                story.append(Paragraph(header_text, style_subheading))
                
                # 內容：進行格式化處理 (處理換行與粗體)
                raw_content = str(analysis.get('content', ''))
                formatted_content = self.format_ai_text(raw_content)
                
                # 加入段落
                story.append(Paragraph(formatted_content, style_normal))
                story.append(Spacer(1, 12))

            # 每檔股票結束後加一條分隔線或換頁
            story.append(Spacer(1, 12))
            story.append(Paragraph("_" * 60, style_normal)) # 分隔線
            story.append(Spacer(1, 24))
            
            # 如果想每檔股票都換頁，可以取消註解下面這行
            # story.append(PageBreak())

        # 5. 生成 PDF
        doc.build(story)
        return filename

        
    def _parse_strategy_key(self, strategy_name: str):
        """
        解析回測策略名稱
        格式範例: Backtest_gemini_gemini-1.5-flash_aggressive
        回傳: (provider, model_name, style)
        """
        try:
            # 移除前綴
            clean = strategy_name.replace("Backtest_", "")
            parts = clean.split("_")
            
            # 因為模型名稱可能包含 "-" 或 ":"，所以拆解要小心
            # 假設 provider 是第一個，style 是最後一個
            provider = parts[0]
            style = parts[-1]
            # 中間剩下的就是 model_name
            model_name = "_".join(parts[1:-1])
            valid_models = ["gpt-oss:20b", "gemma3:12b"]
            if model_name not in valid_models:
                # 如果解析出來的模型不在白名單內，強制使用預設
                model_name = "gpt-oss:20b"
            return provider, model_name, style
        except:
            # 解析失敗回傳預設
            return "ollama", "gpt-oss:20b", "aggressive"

    def generate_pdf(self, filename: str, report_data: list):
        """
        使用 Platypus 引擎製作支援排版的 PDF
        """
        # 1. 註冊中文字型
        font_path = "./resource/TaipeiSansTCBeta-Regular.ttf" 
        font_name = 'TaipeiSansTCBeta-Regular' # 預設 fallback
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
            font_name = 'ChineseFont'
        else:
            print("⚠️ 警告：找不到 font.ttf，中文將無法顯示")

        # 2. 設定文件模板
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )

        # 3. 定義樣式 (Styles)
        styles = getSampleStyleSheet()
        
        # 定義中文普通樣式
        style_normal = ParagraphStyle(
            name='ChineseNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=10,
            leading=14, # 行高
            spaceAfter=6, # 段落後留白
            alignment=TA_LEFT,
            wordWrap='CJK' # 支援中文自動換行
        )

        # 定義中文標題樣式
        style_heading = ParagraphStyle(
            name='ChineseHeading',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=16,
            leading=20,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # 定義 AI 模型標題樣式
        style_subheading = ParagraphStyle(
            name='ChineseSubHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=12,
            leading=16,
            spaceAfter=6,
            textColor=colors.darkred
        )

        # 4. 建立內容 (Story)
        story = []

        # -- 文件標題 --
        story.append(Paragraph("<b>AI 智能選股分析報告</b>", style_heading))
        story.append(Paragraph("本報告由 AI 自動生成，僅供參考，不代表投資建議。", style_normal))
        story.append(Spacer(1, 12)) # 空行

        # -- 遍歷每檔股票 --
        for stock_report in report_data:
            # 股票標題 (例如：【2330 台積電】)
            s_id = str(stock_report.get('stock_id', ''))
            s_name = str(stock_report.get('stock_name', ''))
            s_price = str(stock_report.get('price', 0))
            
            title_text = f"【{s_id} {s_name}】 - 收盤價: {s_price}"
            story.append(Paragraph(title_text, style_heading))
            
            # 技術指標摘要
            strategies = stock_report.get('matched_strategies', [])
            if not isinstance(strategies, list): strategies = [str(strategies)]
            strats_text = ", ".join(strategies)
            trend_text = str(stock_report.get('trend', 'N/A'))
            
            info_text = f"<b>趨勢:</b> {trend_text} | <b>觸發策略:</b> {strats_text}"
            story.append(Paragraph(info_text, style_normal))
            story.append(Spacer(1, 8))

            # AI 分析內容
            for analysis in stock_report.get('analyses', []):
                model_name = str(analysis.get('model', 'Unknown'))
                style_name = str(analysis.get('style', 'Unknown'))
                ret_val = str(analysis.get('return', 0))
                
                # 子標題：模型資訊
                header_text = f"[{model_name} / {style_name}] 分析結果 (回測報酬: {ret_val}%)"
                story.append(Paragraph(header_text, style_subheading))
                
                # 內容：進行格式化處理 (處理換行與粗體)
                raw_content = str(analysis.get('content', ''))
                formatted_content = self.format_ai_text(raw_content)
                
                # 加入段落
                story.append(Paragraph(formatted_content, style_normal))
                story.append(Spacer(1, 12))

            # 每檔股票結束後加一條分隔線或換頁
            story.append(Spacer(1, 12))
            story.append(Paragraph("_" * 60, style_normal)) # 分隔線
            story.append(Spacer(1, 24))
            
            # 如果想每檔股票都換頁，可以取消註解下面這行
            # story.append(PageBreak())

        # 5. 生成 PDF
        doc.build(story)
        return filename

    def run_comprehensive_analysis(self, db: Session, req_data):
        """
        執行完整流程：篩選 -> 決策 -> 分析 -> PDF
        """
        # 1. 篩選股票
        # 使用 stock_service 現有的功能
        screen_results = self.stock_service.screen_stocks(
            strategies=req_data.strategies,
            scope="Custom",
            custom_list=req_data.custom_tickers
        )
        final_report_data = []

        # 2. 針對每一檔篩選出來的股票
        for item in screen_results:
            stock_id = item['stock_id']
            stock_name = item['name']
            
            # 準備技術數據
            df = self.stock_service.fetch_data(stock_id)
            df = self.stock_service.calculate_indicators(df)
            summary = self.stock_service.get_technical_summary(df)
            
            # 3. 找出最佳模型組合
            # 查詢回測紀錄，依報酬率排序，取前 2 名
            top_records = db.query(models.BacktestRecord)\
                .filter(models.BacktestRecord.stock_id == stock_id)\
                .order_by(desc(models.BacktestRecord.result_data))\
                .all()
            # 因為 result_data 是字串，不能直接在 SQL 排序 JSON 欄位 (除非用 PostgreSQL JSONB)
            # 這裡簡單處理：撈出來後用 Python 排序
            parsed_records = []
            for r in top_records:
                try:
                    res_json = json.loads(r.result_data)
                    ret = res_json.get('total_return_pct', -999)
                    parsed_records.append({"record": r, "return": ret})
                except:
                    pass
            
            # 排序取 Top 2
            parsed_records.sort(key=lambda x: x['return'], reverse=True)
            best_2 = parsed_records[:2]
            
            analyses = []
            
            # 如果沒有紀錄，使用預設 (gpt-oss:20b + aggressive)
            if not best_2:
                # 預設組合
                target_configs = [{
                    "provider": "ollama",
                    "model": "gpt-oss:20b",
                    "style": "aggressive",
                    "return_pct": "N/A (無紀錄)"
                }]
            else:
                target_configs = []
                for p in best_2:
                    rec = p['record']
                    prov, mod, style = self._parse_strategy_key(rec.strategy_name)
                    target_configs.append({
                        "provider": prov,
                        "model": mod,
                        "style": style,
                        "return_pct": p['return']
                    })

            # 4. 執行 AI 分析
            for config in target_configs:
                try:
                    print(f"Analysis {stock_id}")
                    # 呼叫 AI (文字報告)
                    ai_text = self.ai_service.get_analysis(
                        api_key="",
                        stock_id=stock_id,
                        stock_name=stock_name,
                        mode="Long", # 選股通常是做多
                        cost=summary['close'],
                        context_data=summary['context_str'],
                        provider="ollama",
                        model_name=config['model'],
                        ollama_url=req_data.ollama_url,
                        prompt_style=config['style']
                    )
                    
                    analyses.append({
                        "model": config['model'],
                        "style": config['style'],
                        "return": config['return_pct'],
                        "content": ai_text
                    })
                except Exception as e:
                    print(f"Analysis failed for {stock_id}: {e}")

            # 收集結果
            final_report_data.append({
                "stock_id": stock_id,
                "stock_name": stock_name,
                "price": summary['close'],
                "trend": summary['trend'],
                "matched_strategies": item['matched_strategies'],
                "analyses": analyses
            })

        # 5. 生成 PDF
        output_filename = "analysis_report.pdf"
        self.generate_pdf(output_filename, final_report_data)
        
        return output_filename