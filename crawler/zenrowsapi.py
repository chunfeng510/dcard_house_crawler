# pip install zenrows
from zenrows import ZenRowsClient
import json
import re
import os
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import time
import sys

# 導入系統設置
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    BASE_URL, FORUM_NAME, HEADERS, POSTS_LIMIT, TOTAL_POSTS,
    DELAY_BETWEEN_REQUESTS
)
from database.db_manager import DatabaseManager
from utils.helpers import save_last_id, load_last_id

# 設定日誌
logger = logging.getLogger(__name__)

class ZenRowsApiCrawler:
    """使用 ZenRows API 的 Dcard 爬蟲類"""
    
    def __init__(self, api_key="3d16f55e44b51fc52353566769dce39bfe0c5c58", forum_name=None, continue_last=True):
        """初始化爬蟲"""
        self.client = ZenRowsClient(api_key)
        self.base_url = BASE_URL
        self.forum_name = forum_name or FORUM_NAME
        self.forum_url = f"{BASE_URL}/forums/{self.forum_name}/posts"
        self.save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw_posts')
        os.makedirs(self.save_dir, exist_ok=True)
        self.continue_last = continue_last  # 是否從上次爬取的位置繼續
        
        # 初始化資料庫連接
        self.db = DatabaseManager()
        self.db.connect()
        self.db.initialize_db()

    def fetch_posts(self, limit=POSTS_LIMIT, before=None):
        """獲取文章列表"""
        try:
            url = self.forum_url
            params = {
                "js_render": "true",
                "json_response": "true"                
            }
            if before:
                url += f"?before={before}&limit={limit}"
            else:
                url += f"?limit={limit}"       
            # 添加限制參數 limit 是以 url query string 的形式傳遞

            logger.info(f"開始獲取文章列表: {url}")
            response = self.client.get(url, params=params)

            if '"html":' in response.text:
                json_content = json.loads(response.text)
                posts_data = json.loads(json_content['html'])
                
                # 保存原始數據
                self._save_raw_data(url, posts_data)
                
                # 保存到資料庫
                self._save_to_database(posts_data)
                
                logger.info(f"成功獲取 {len(posts_data)} 篇文章")
                return posts_data
            else:
                logger.error("響應中未找到文章數據")
                return []

        except Exception as e:
            logger.error(f"獲取文章列表失敗: {e}")
            self._save_error_response(url, response.text)
            return []

    def _save_raw_data(self, url, posts_data):
        """保存原始數據到文件"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            limit = query_params.get('limit', ['unknown'])[0]
            
            filename = f'dcard_posts_limit{limit}_{timestamp}.json'
            filepath = os.path.join(self.save_dir, filename)
            
            output_data = {
                "url": url,
                "fetch_time": datetime.now().isoformat(),
                "posts": posts_data
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"原始數據已保存到: {filename}")
            
        except Exception as e:
            logger.error(f"保存原始數據失敗: {e}")

    def _save_to_database(self, posts_data):
        """保存數據到資料庫"""
        try:
            for post in posts_data:
                self.db.insert_post(post)
        except Exception as e:
            logger.error(f"保存到資料庫失敗: {e}")

    def _save_error_response(self, url, response_text):
        """保存錯誤響應"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            error_filepath = os.path.join(self.save_dir, f'error_response_{timestamp}.txt')
            
            with open(error_filepath, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n\n")
                f.write(response_text)
                
            logger.error(f"錯誤響應已保存到: {error_filepath}")
            
        except Exception as e:
            logger.error(f"保存錯誤響應失敗: {e}")

    def crawl(self, total_posts=TOTAL_POSTS):
        """開始爬取指定數量的文章"""
        try:
            posts_count = 0
            last_id = None
            
            # 如果需要繼續上次的爬取，則讀取保存的 last_id
            if self.continue_last:
                saved_last_id = load_last_id(self.forum_name)
                if saved_last_id:
                    last_id = saved_last_id
                    logger.info(f"繼續從上次爬取的位置開始，last_id: {last_id}")
                else:
                    logger.info("沒有找到上次爬取的位置，將從頭開始爬取")
            
            while posts_count < total_posts:
                posts = self.fetch_posts(before=last_id)
                
                if not posts:
                    logger.warning("沒有更多文章或請求失敗")
                    break
                    
                posts_count += len(posts)
                
                if posts:
                    last_id = posts[-1].get('id')
                    # 保存最後一篇文章的ID，以便下次繼續爬取
                    save_last_id(last_id, self.forum_name)
                    
                logger.info(f"已處理 {posts_count}/{total_posts} 篇文章，最後ID: {last_id}")
                
                # 在請求之間添加延遲
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            return True
            
        except Exception as e:
            logger.error(f"爬取過程中發生錯誤: {e}")
            # 即使出錯，也要保存最後爬取的ID
            if last_id:
                save_last_id(last_id, self.forum_name)
            return False
            
        finally:
            self.db.close()

    def close(self):
        """關閉資源"""
        self.db.close()


# 測試執行
if __name__ == "__main__":
    crawler = ZenRowsApiCrawler()
    crawler.crawl(total_posts=10)
    crawler.close()