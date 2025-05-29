"""
Dcard爬蟲模組 - 使用Selenium繞過Cloudflare保護
"""
import os
import sys
import time
import json
import logging
import requests
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    BASE_URL, FORUM_NAME, HEADERS, POSTS_LIMIT, TOTAL_POSTS, 
    DELAY_BETWEEN_REQUESTS, USE_PROXY, PROXY_LIST, ROTATE_PROXY
)
from database.db_manager import DatabaseManager

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'crawler.log'),
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

class DcardCrawler:
    """Dcard爬蟲類別，使用Selenium繞過Cloudflare保護"""
    
    def __init__(self):
        """初始化爬蟲"""
        self.base_url = BASE_URL
        self.forum_url = f"{BASE_URL}/forums/{FORUM_NAME}/posts"
        self.headers = HEADERS
        self.db = DatabaseManager()
        self.db.connect()
        self.db.initialize_db()
        self.driver = None
        
    def setup_selenium(self):
        """設置Selenium"""
        try:
            chrome_options = Options()
            # 建議在正式運行時移除 headless 選項，以便通過Cloudflare的檢查
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(SELENIUM_IMPLICIT_WAIT)
            logger.info("Selenium設置成功")
            return True
        except WebDriverException as e:
            logger.error(f"Selenium設置失敗: {e}")
            return False
            
    def bypass_cloudflare(self):
        """繞過Cloudflare保護"""
        try:
            logger.info("嘗試繞過Cloudflare保護...")
            self.driver.get("https://www.dcard.tw/f/house_purchase")  # 先訪問普通頁面
            
            # 等待頁面加載完成
            WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待一段時間，讓Cloudflare檢查通過
            time.sleep(5)
            
            # 獲取cookies
            cookies = self.driver.get_cookies()
            self.session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
            
            logger.info("成功繞過Cloudflare保護")
            return True
        except Exception as e:
            logger.error(f"繞過Cloudflare失敗: {e}")
            return False
            
    def fetch_posts(self, before=None, limit=POSTS_LIMIT):
        """獲取文章列表"""
        try:
            url = self.forum_url
            params = {'limit': limit}
            
            if before:
                params['before'] = before
                
            # 建立一個session並加入cookies
            session = requests.Session()
            for name, value in self.session_cookies.items():
                session.cookies.set(name, value)
                
            # 發送請求
            response = session.get(url, params=params, headers=self.headers)
            
            if response.status_code == 200:
                posts_data = response.json()
                logger.info(f"成功獲取{len(posts_data)}篇文章")
                return posts_data
            else:
                logger.error(f"請求失敗: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"獲取文章列表失敗: {e}")
            return []
            
    def fetch_post_content(self, post_id):
        """獲取單篇文章內容"""
        try:
            url = f"{self.base_url}/{post_id}"
            
            # 建立一個session並加入cookies
            session = requests.Session()
            for name, value in self.session_cookies.items():
                session.cookies.set(name, value)
                
            # 發送請求
            response = session.get(url, headers=self.headers)
            
            if response.status_code == 200:
                post_data = response.json()
                logger.info(f"成功獲取文章內容: {post_data.get('title')}")
                return post_data
            else:
                logger.error(f"獲取文章內容失敗: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"獲取文章內容失敗: {e}")
            return None
            
    def process_post(self, post):
        """處理單篇文章數據"""
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
            
    def crawl(self):
        """爬取文章主函數"""
        try:
            # 設置Selenium並繞過Cloudflare
            if not self.setup_selenium() or not self.bypass_cloudflare():
                logger.error("無法設置爬蟲環境")
                return False
                
            posts_count = 0
            last_id = None
            
            while posts_count < TOTAL_POSTS:
                # 獲取文章列表
                posts = self.fetch_posts(before=last_id)
                
                if not posts:
                    logger.warning("沒有更多文章或請求失敗")
                    break
                    
                # 處理每篇文章
                for post in posts:
                    if self.process_post(post):
                        posts_count += 1
                        
                    if posts_count >= TOTAL_POSTS:
                        break
                        
                # 記錄最後一篇文章的ID用於分頁
                if posts:
                    last_id = posts[-1].get('id')
                    
                logger.info(f"已處理 {posts_count}/{TOTAL_POSTS} 篇文章")
                
                # 延遲避免請求過快
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            return True
        except Exception as e:
            logger.error(f"爬取過程中發生錯誤: {e}")
            return False
        finally:
            # 關閉資源
            if self.driver:
                self.driver.quit()
            self.db.close()

# 測試執行
if __name__ == "__main__":
    crawler = DcardCrawler()
    crawler.crawl()