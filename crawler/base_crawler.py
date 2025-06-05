"""
基礎爬蟲模組 - 定義所有爬蟲實現的共同介面
"""
import os
import sys
import logging
import time
from datetime import datetime
from abc import ABC, abstractmethod

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    BASE_URL, FORUM_NAME, HEADERS, POSTS_LIMIT, TOTAL_POSTS, 
    DELAY_BETWEEN_REQUESTS
)
from database.db_manager import DatabaseManager

# 設定日誌
logger = logging.getLogger(__name__)

class BaseCrawler(ABC):
    """Dcard基礎爬蟲抽象類別，定義所有爬蟲必須實現的方法"""
    
    def __init__(self):
        """初始化基礎爬蟲類別"""
        self.base_url = BASE_URL
        self.forum_url = f"{BASE_URL}/forums/{FORUM_NAME}/posts"
        self.headers = HEADERS
        self.db = DatabaseManager()
        self.db.connect()
        self.db.initialize_db()
        
    @abstractmethod
    def fetch_posts(self, before=None, limit=POSTS_LIMIT):
        """獲取文章列表（抽象方法，子類必須實現）"""
        pass
            
    @abstractmethod
    def fetch_post_content(self, post_id):
        """獲取單篇文章內容（抽象方法，子類必須實現）"""
        pass
            
    def process_post(self, post):
        """處理單篇文章數據（可被子類覆寫）"""
        try:
            post_id = post.get('id')
            post_content = self.fetch_post_content(post_id)
            
            if post_content:
                title = post_content.get('title', '')
                content = post_content.get('content', '')
                created_at = post_content.get('createdAt', '')
                
                # 格式化日期
                if created_at:
                    try:
                        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_at = created_at_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        logger.warning(f"日期格式化失敗: {created_at}")
                
                # 存入資料庫
                self.db.insert_post(title, content, created_at)
                
                # 延遲避免請求過快
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                return True
            return False
        except Exception as e:
            logger.error(f"處理文章失敗: {e}")
            return False
            
    @abstractmethod
    def setup(self):
        """設置爬蟲環境（抽象方法，子類必須實現）"""
        pass
    
    @abstractmethod
    def crawl(self):
        """爬取文章主函數（抽象方法，子類必須實現）"""
        pass
    
    def close(self):
        """關閉資源（可被子類覆寫）"""
        if hasattr(self, 'db') and self.db:
            self.db.close()
            logger.info("資料庫連接已關閉")