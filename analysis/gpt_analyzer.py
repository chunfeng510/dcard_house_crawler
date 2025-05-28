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
from openai import OpenAI, AzureOpenAI

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'analysis.log'),
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

class GPTAnalyzer:
    """使用 GPT 分析 Dcard 房屋文章的類別"""
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo", endpoint_url=None, api_version="2024-12-01-preview", deployment=None):
        """初始化 GPT 分析器"""
        self.db = DatabaseManager()
        self.db.connect()
        
        # 設定 OpenAI API key
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("未設定 OpenAI API key，請設定環境變數 OPENAI_API_KEY 或在初始化時提供")
        
        # 設定 API 端點 URL (主要用於 Azure OpenAI 服務)
        self.endpoint_url = endpoint_url or os.environ.get("ENDPOINT_URL")
        self.model = model
        self.deployment = deployment or os.environ.get("AZURE_DEPLOYMENT_NAME", model)
        self.api_version = api_version
        
        # 初始化 API 客戶端
        if self.endpoint_url and "azure" in self.endpoint_url:
            logger.info(f"使用 Azure OpenAI API，端點: {self.endpoint_url}")
            self.client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=self.endpoint_url,
                api_key=self.api_key
            )
            self.is_azure = True
        else:
            logger.info("使用標準 OpenAI API")
            self.client = OpenAI(api_key=self.api_key)
            self.is_azure = False
    
    def analyze_posts(self):
        """分析所有尚未分析過的文章"""
        logger.info("開始使用 GPT 分析文章...")
        
        # 取得所有未分析的文章
        posts = self.db.get_posts_for_analysis()
        
        if not posts:
            logger.info("沒有需要分析的文章")
            return True
        
        logger.info(f"共有 {len(posts)} 篇文章需要分析")
        
        success_count = 0
        for post in posts:
            post_id, title, content = post[0], post[1], post[2]
            
            if not content:
                logger.warning(f"文章內容為空: {title}")
                continue
            
            try:
                # 分析文章與房貸主題的相關程度
                relevance_score, structured_data = self.analyze_with_gpt(title, content)
                
                # 儲存分析結果
                structured_data_json = json.dumps(structured_data, ensure_ascii=False)
                if self.db.update_post_analysis(post_id, relevance_score, structured_data_json):
                    success_count += 1
                    logger.info(f"成功分析文章: {title}")
                
                # 防止 API 請求過於頻繁
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"分析文章 '{title}' 時發生錯誤: {e}")
                
        logger.info(f"成功分析 {success_count}/{len(posts)} 篇文章")
        return success_count > 0
    
    def analyze_with_gpt(self, title, content):
        """使用 GPT 分析文章標題和內容"""
        try:
            # 將標題與內容結合起來進行分析
            text_to_analyze = f"標題: {title}\n\n內容: {content}"
            
            # 定義系統提示詞
            system_prompt = """
            你是一位專業的房地產與房貸分析專家。請分析提供的Dcard房屋版文章，執行兩項任務:
            
            1. 評估文章與「房貸」主題的相關程度，給出0-100的分數。
               - 0分表示完全無關
               - 100分表示非常相關，主要討論房貸
            
            2. 從文章中提取結構化資訊(如有提及)，包括:
               - 房貸金額
               - 房貸利率
               - 貸款年限
               - 貸款成數
               - 月付金額
               - 提到的銀行名稱列表
            
            請以JSON格式回覆，不要包含解釋，範例:
            {
                "relevance_score": 85,
                "structured_data": {
                    "房貸金額": "500萬",
                    "房貸利率": "1.31%",
                    "貸款年限": "30年",
                    "貸款成數": "80成",
                    "月付金額": "21000",
                    "提到的銀行": ["台銀", "土銀"]
                }
            }
            """
            
            # 發送 API 請求
            if self.is_azure:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_to_analyze}
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                    model=self.deployment
                )
            else:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text_to_analyze}
                    ],
                    temperature=0.3,
                    max_tokens=1000,
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
                relevance_score = result.get("relevance_score", 0)
                structured_data = result.get("structured_data", {})
                
                logger.info(f"GPT 分析完成: 相關度分數 = {relevance_score}")
                return relevance_score, structured_data
            else:
                logger.error("無法從 GPT 回應中解析 JSON 結果")
                return 0, {}
            
        except Exception as e:
            logger.error(f"GPT 分析失敗: {e}")
            return 0, {}

if __name__ == "__main__":
    # 可以在這裡設置 API 金鑰或使用環境變數
    endpoint_url = os.getenv("ENDPOINT_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    deployment = os.getenv("AZURE_DEPLOYMENT_NAME")
    analyzer = GPTAnalyzer(api_key=api_key, endpoint_url=endpoint_url, deployment=deployment)
    analyzer.analyze_posts()