"""
使用 GPT 分析 Dcard 房屋文章的模組
- 判斷文章與「房貸」主題的相關程度
- 將文章內容轉為結構化資訊
"""
import os
import sys
import json
import logging
from datetime import datetime
import re
import time
import sqlite3
from openai import OpenAI, AzureOpenAI

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from config import settings

# 設定日誌
logger = logging.getLogger(__name__)

class GPTAnalyzer:
    """使用 GPT 分析 Dcard 房屋文章的類別"""
    
    def __init__(self, api_key=None, model=None, endpoint_url=None, api_version=None, deployment=None):
        """初始化 GPT 分析器"""
        self.db = DatabaseManager()
        self.db.connect()
        
        # 從 settings.py 或參數讀取設定
        self.api_key = api_key or settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        self.model = model or settings.GPT_MODEL
        self.max_tokens = settings.GPT_MAX_TOKENS
        self.temperature = settings.GPT_TEMPERATURE
        self.use_azure = settings.USE_AZURE_OPENAI
        self.api_delay = settings.GPT_API_DELAY
        self.min_confidence_score = settings.MIN_CONFIDENCE_SCORE
        
        # Azure OpenAI 相關設定
        if self.use_azure:
            self.endpoint_url = endpoint_url or settings.AZURE_ENDPOINT_URL
            self.api_version = api_version or settings.AZURE_API_VERSION
            self.deployment = deployment or settings.AZURE_DEPLOYMENT_NAME or self.model
        else:
            self.endpoint_url = endpoint_url
            self.api_version = api_version or "2024-12-01-preview"
            self.deployment = deployment
        
        if not self.api_key:
            logger.warning("未設定 OpenAI API key，請在 settings.py 中設定 OPENAI_API_KEY 或透過環境變數提供")
        
        # 初始化 API 客戶端
        if self.use_azure and self.endpoint_url:
            logger.info(f"使用 Azure OpenAI API，端點: {self.endpoint_url}")
            logger.info(f"使用模型: {self.model}")
            logger.info(f"部署名稱: {self.deployment}")
            
            self.client = AzureOpenAI(
                api_version=self.api_version,
                azure_endpoint=self.endpoint_url,
                api_key=self.api_key
            )
            self.is_azure = True
        else:
            logger.info("使用標準 OpenAI API")
            logger.info(f"使用模型: {self.model}")
            logger.info(f"模型設定: 最大 Token: {self.max_tokens}, 溫度: {self.temperature}")
            
            self.client = OpenAI(api_key=self.api_key)
            self.is_azure = False
            
    def get_unanalyzed_content(self, limit=None):
        """取得未分析的文章內容"""
        try:
            if limit is None:
                limit = settings.ANALYSIS_BATCH_SIZE
                
            cursor = self.db.conn.cursor()
            
            query = """
            SELECT p.id, p.title, pc.content
            FROM posts p
            JOIN post_content pc ON p.id = pc.post_id
            WHERE NOT EXISTS (
                SELECT 1 FROM content_analysis ca 
                WHERE ca.post_id = p.id AND ca.data_type = 'content'
            )
            AND NOT EXISTS (
                -- 排除已知相關度為0的文章
                SELECT 1 FROM content_analysis ca 
                WHERE ca.post_id = p.id AND ca.data_type = 'content' AND ca.confidence_score = 0
            )
            LIMIT ?
            """
            
            cursor.execute(query, (limit,))
            posts = cursor.fetchall()
            return posts
            
        except sqlite3.Error as e:
            logger.error(f"取得未分析文章內容失敗: {e}")
            return []
    
    def get_unanalyzed_comments(self, limit=None):
        """取得未分析的留言內容"""
        try:
            if limit is None:
                limit = settings.COMMENT_ANALYSIS_BATCH_SIZE
                
            cursor = self.db.conn.cursor()
            
            query = """
            SELECT pc.id, pc.post_id, pc.content
            FROM post_comments pc
            WHERE NOT EXISTS (
                SELECT 1 FROM content_analysis ca 
                WHERE ca.comment_id = pc.id
            )
            AND NOT EXISTS (
                -- 排除已知相關度為0的留言
                SELECT 1 FROM content_analysis ca 
                WHERE ca.comment_id = pc.id AND ca.confidence_score = 0
            )
            AND length(pc.content) > ?
            LIMIT ?
            """
            
            cursor.execute(query, (settings.MIN_COMMENT_LENGTH, limit))
            comments = cursor.fetchall()
            return comments
            
        except sqlite3.Error as e:
            logger.error(f"取得未分析留言內容失敗: {e}")
            return []
    
    def analyze_post_contents(self, batch_size=None):
        """分析所有尚未分析過的文章內容"""
        logger.info("開始使用 GPT 分析文章內容...")
        
        # 取得未分析的文章內容
        if batch_size is None:
            batch_size = settings.ANALYSIS_BATCH_SIZE
            
        posts = self.get_unanalyzed_content(batch_size)
        
        if not posts:
            logger.info("沒有需要分析的文章內容")
            return True
        
        logger.info(f"共有 {len(posts)} 篇文章內容需要分析")
        
        success_count = 0
        skipped_count = 0
        for post in posts:
            post_id, title, content = post[0], post[1], post[2]
            
            if not content:
                logger.warning(f"文章內容為空: {title}")
                continue
            
            try:
                # 分析文章內容
                confidence_score, structured_data = self.analyze_with_gpt(title, content)
                
                # 無論相關度分數如何，都保存結果到資料庫
                # 這樣下次就能跳過相關度為0的項目
                if confidence_score == 0:
                    # 相關度為0，保存一個空的結構化數據以標記已處理
                    empty_data = {}
                    self.save_content_analysis(post_id, None, 'content', 0, empty_data)
                    skipped_count += 1
                    logger.info(f"文章 '{title}' (ID: {post_id}) 與房貸主題不相關 (相關度為0)，已標記為不需再分析")
                    continue
                
                # 處理每個結構化數據項目
                if isinstance(structured_data, list):
                    # 如果是多筆資料，處理每筆
                    for data_item in structured_data:
                        self.save_content_analysis(post_id, None, 'content', confidence_score, data_item)
                else:
                    # 單筆資料
                    self.save_content_analysis(post_id, None, 'content', confidence_score, structured_data)
                
                success_count += 1
                logger.info(f"成功分析文章內容: {title}")
                
                # 防止 API 請求過於頻繁
                time.sleep(self.api_delay)
                
            except Exception as e:
                logger.error(f"分析文章內容 '{title}' (ID: {post_id}) 時發生錯誤: {e}")
                
        logger.info(f"成功分析 {success_count}/{len(posts)} 篇文章內容，跳過 {skipped_count} 篇不相關文章")
        return success_count > 0
    
    def analyze_post_comments(self, batch_size=None):
        """分析所有尚未分析過的文章留言"""
        logger.info("開始使用 GPT 分析文章留言...")
        
        # 取得未分析的留言
        if batch_size is None:
            batch_size = settings.COMMENT_ANALYSIS_BATCH_SIZE
            
        comments = self.get_unanalyzed_comments(batch_size)
        
        if not comments:
            logger.info("沒有需要分析的留言")
            return True
        
        logger.info(f"共有 {len(comments)} 則留言需要分析")
        
        success_count = 0
        skipped_count = 0
        for comment in comments:
            comment_id, post_id, content = comment[0], comment[1], comment[2]
            
            if not content or len(content.strip()) < settings.MIN_COMMENT_LENGTH:
                logger.debug(f"留言內容過短或為空: {comment_id}")
                continue
            
            try:
                # 分析留言內容
                confidence_score, structured_data = self.analyze_with_gpt("", content)
                
                # 無論相關度分數如何，都保存結果到資料庫
                # 這樣下次就能跳過相關度為0的項目
                if confidence_score == 0:
                    # 相關度為0，保存一個空的結構化數據以標記已處理
                    empty_data = {}
                    self.save_content_analysis(post_id, comment_id, 'comment', 0, empty_data)
                    skipped_count += 1
                    logger.info(f"留言 {comment_id} 與房貸主題不相關 (相關度為0)，已標記為不需再分析")
                    continue
                
                # 如果相關性太低，仍然保存但不做後續處理
                if confidence_score < self.min_confidence_score:
                    logger.debug(f"留言 {comment_id} 與房貸主題相關性太低 ({confidence_score})")
                    empty_data = {}
                    self.save_content_analysis(post_id, comment_id, 'comment', confidence_score, empty_data)
                    continue
                
                # 處理每個結構化數據項目
                if isinstance(structured_data, list):
                    # 如果是多筆資料，處理每筆
                    for data_item in structured_data:
                        self.save_content_analysis(post_id, comment_id, 'comment', confidence_score, data_item)
                else:
                    # 單筆資料
                    self.save_content_analysis(post_id, comment_id, 'comment', confidence_score, structured_data)
                
                success_count += 1
                logger.info(f"成功分析留言: {comment_id}")
                
                # 防止 API 請求過於頻繁
                time.sleep(self.api_delay)
                
            except Exception as e:
                logger.error(f"分析留言 '{comment_id}' 時發生錯誤: {e}")
                
        logger.info(f"成功分析 {success_count}/{len(comments)} 則留言，跳過 {skipped_count} 則不相關留言")
        return success_count > 0
    
    def save_content_analysis(self, post_id, comment_id, data_type, confidence_score, structured_data):
        """將分析結果存入數據庫"""
        try:
            # 準備分析數據
            analysis_data = {
                'data_type': data_type,
                'post_id': post_id,
                'comment_id': comment_id,
                'house_price': structured_data.get('house_price'),
                'loan_amount': structured_data.get('loan_amount'),
                'interest_rate': structured_data.get('interest_rate'),
                'loan_term': structured_data.get('loan_term'),
                'loan_to_value_ratio': structured_data.get('loan_to_value_ratio'),
                'monthly_payment': structured_data.get('monthly_payment'),
                'grace_period': structured_data.get('grace_period'),
                'bank': structured_data.get('bank'),
                'loan_type': structured_data.get('loan_type'),
                'real_estate_area': structured_data.get('real_estate_area'),
                'loaner_income_monthly': structured_data.get('loaner_income_monthly'),
                'loaner_income_yearly': structured_data.get('loaner_income_yearly'),
                'loaner_occupation': structured_data.get('loaner_occupation'),
                'background_time': structured_data.get('background_time'),
                'confidence_score': confidence_score
            }
            
            # 存入數據庫
            return self.db.insert_content_analysis(analysis_data)
            
        except Exception as e:
            logger.error(f"儲存分析結果時發生錯誤: {e}")
            return False
    
    def analyze_with_gpt(self, title, content):
        """使用 GPT 分析文章標題和內容"""
        try:
            # 將標題與內容結合起來進行分析
            text_to_analyze = f"標題: {title}\n\n內容: {content}"
            
            # 定義系統提示詞
            system_prompt = """
            你是一位專業的房地產與房貸分析專家。請分析我提供的Dcard房屋版文章內容或是留言，執行兩項任務:
            
            1. 評估內容與「房貸」主題的相關程度，給出0-100的分數。
               - 0分表示與房貸完全無關
               - 100分表示非常相關，主要都在討論房貸
            
            2. 從內容中提取結構化資訊(如有提及)，包括:
               - house_price: 房屋總價
               - loan_amount: 房貸金額
               - interest_rate: 房貸利率
               - loan_term: 貸款年限
               - loan_to_value_ratio: 貸款成數
               - monthly_payment: 月付金額
               - grace_period: 寬限期資訊
               - bank: 提到的銀行名稱
               - loan_type: 貸款類型(如:新青安、一般房貸等)
               - real_estate_area: 相關房市區域
               - loaner_income_monthly: 貸款人收入(月薪)
               - loaner_income_yearly: 貸款人收入(年薪)
               - loaner_occupation: 貸款人職業(如: 老師、工程師、科技業)
               - background_time: 記錄這個資訊的時空(如:2025年4月詢問銀行的)
            
            請以JSON格式回覆，不要包含解釋，若銀行,貸款成數,利率...等資料有多筆，可以拆成多筆，注意配對順序，範例:
            {
                "confidence_score": 85,
                "structured_data": [{
                    "house_price": "1000萬",
                    "loan_amount": "500萬",
                    "interest_rate": "1.31%,2.4%",
                    "loan_term": "30年,40年",
                    "loan_to_value_ratio": "8成,85成",
                    "monthly_payment": "21000",
                    "grace_period": "6個月",
                    "bank": "台銀,土銀",
                    "loan_type": "一般房貸",
                    "real_estate_area": "台北市松山區",
                    "loaner_income_monthly": "5萬",
                    "loaner_income_yearly": "60萬",
                    "loaner_occupation": "工程師",
                    "background_time": "2025年4月"
                }, {
                    "house_price": "1500萬",
                    "loan_amount": "300萬",
                    "interest_rate": "1.25%",
                    "loan_term": "20年",
                    "loan_to_value_ratio": "70成",
                    "monthly_payment": "15000",
                    "grace_period": "3年",
                    "bank": "合作金庫",
                    "loan_type": "新青安方案",
                    "real_estate_area": "新北市新店區",
                    "loaner_income_monthly": "8萬",
                    "loaner_income_yearly": "96萬",
                    "loaner_occupation": "科技業",
                    "background_time": "2024年12月"
                }]
            }
            
            請注意：
            - 若找不到某項資料則該欄位留空
            - 若有多家銀行，僅使用一個欄位用逗號分隔，例如：「台銀,土銀,合庫」
            - 給予合理且符合實際內容的相關程度分數
            """
            
            # 發送 API 請求
            if self.is_azure:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_to_analyze}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    model=self.deployment
                )
            else:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_to_analyze}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    model=self.model
                )
            
            # 解析回應
            response_text = response.choices[0].message.content.strip()
            
            # 查找並提取 JSON 部分
            json_match = re.search(r'{.*}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                result = json.loads(json_text)
                
                # 提取相關度分數和結構化數據
                confidence_score = result.get("confidence_score", 0)
                structured_data = result.get("structured_data", {})
                
                logger.info(f"GPT 分析完成: 相關度分數 = {confidence_score}")
                return confidence_score, structured_data
            else:
                logger.error("無法從 GPT 回應中解析 JSON 結果")
                return 0, {}
            
        except Exception as e:
            logger.error(f"GPT 分析失敗: {e}")
            return 0, {}

if __name__ == "__main__":
    # 從 settings.py 讀取設定
    analyzer = GPTAnalyzer()
    
    # 分析文章內容
    print("開始分析文章內容...")
    analyzer.analyze_post_contents()
    
    # 分析留言內容
    print("開始分析文章留言...")
    analyzer.analyze_post_comments()