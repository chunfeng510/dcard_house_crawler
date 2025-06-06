"""
Dcard爬蟲模組 - 使用 ScraperAPI 繞過網站限制
"""
import os
import sys
import time
import json
import logging
import requests
import urllib3
import random
from datetime import datetime

# 停用不安全的 HTTPS 警告（僅用於開發/測試環境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    BASE_URL, FORUM_NAME, HEADERS, POSTS_LIMIT, TOTAL_POSTS, 
    DELAY_BETWEEN_REQUESTS, USE_PROXY, PROXY_LIST, ROTATE_PROXY
)
from crawler.base_crawler import BaseCrawler, logger
from utils.helpers import retry, save_last_id, load_last_id

class ScraperApiCrawler(BaseCrawler):
    """Dcard爬蟲類別，使用 ScraperAPI 繞過網站保護"""
    
    def __init__(self, api_key='874493b63edbe6b44362b48525886d6c', render=True, forum_name=None, continue_last=True):
        """初始化爬蟲"""
        super().__init__()  # 調用父類別初始化方法
        self.api_key = api_key
        self.render = render  # 是否啟用 JavaScript 渲染
        self.api_base_url = 'https://api.scraperapi.com/'
        self.forum_name = forum_name or FORUM_NAME
        self.continue_last = continue_last  # 是否從上次爬取的位置繼續
        
    def setup(self):
        """設置爬蟲環境"""
        # 不執行API測試，直接返回成功
        logger.info("ScraperAPI 爬蟲環境設置完成")
        return True
    
    @retry(max_tries=3, delay=2.0, backoff_factor=2.0, 
           exceptions=(requests.RequestException, requests.ConnectionError, requests.Timeout, json.JSONDecodeError))
    def _make_api_request(self, target_url, params=None):
        """使用 ScraperAPI 發送請求（帶有重試機制）"""
        api_params = {
            'api_key': self.api_key,
            'url': target_url
        }
        
        # 如果需要渲染 JavaScript
        if self.render:
            api_params['render'] = 'true'
        
        # 合併自定義參數
        if params:
            # 將參數添加到目標 URL
            if '?' in target_url:
                target_url += '&' + '&'.join([f"{k}={v}" for k, v in params.items()])
            else:
                target_url += '?' + '&'.join([f"{k}={v}" for k, v in params.items()])
            api_params['url'] = target_url
        
        # 設置代理
        proxies = None
        if USE_PROXY and PROXY_LIST:
            proxy = random.choice(PROXY_LIST) if ROTATE_PROXY else PROXY_LIST[0]
            proxies = {
                'http': proxy,
                'https': proxy,
            }
            logger.info(f"使用代理: {proxy}")
        
        # 發送請求
        response = requests.get(
            self.api_base_url,
            params=api_params,
            proxies=proxies,
            verify=False,
            headers=self.headers,
            timeout=60  # 設置較長的超時時間，因為 ScraperAPI 可能需要時間
        )
        
        # 檢查響應狀態碼
        if response.status_code >= 400:
            error_msg = f"API請求失敗，狀態碼: {response.status_code}"
            logger.error(error_msg)
            response.raise_for_status()  # 這會觸發重試機制
            
        return response
            
    def fetch_posts(self, before=None, limit=POSTS_LIMIT):
        """獲取文章列表"""
        try:
            params = {'limit': limit}
            if before:
                params['before'] = before
            
            target_url = self.forum_url
            response = self._make_api_request(target_url, params)
            
            if response and response.status_code == 200:
                posts_data = response.json()
                logger.info(f"成功獲取{len(posts_data)}篇文章")
                return posts_data
            else:
                logger.error(f"請求失敗: {response.status_code if response else 'No response'}")
                return []
        except Exception as e:
            logger.error(f"獲取文章列表失敗: {e}")
            return []
            
    def fetch_post_content(self, post_id):
        """獲取單篇文章內容"""
        try:
            target_url = f"{self.base_url}/posts/{post_id}"
            response = self._make_api_request(target_url)
            
            if response and response.status_code == 200:
                post_data = response.json()
                logger.info(f"成功獲取文章內容: {post_data.get('title')}")
                return post_data
            else:
                logger.error(f"獲取文章內容失敗: {response.status_code if response else 'No response'}")
                return None
        except Exception as e:
            logger.error(f"獲取文章內容失敗: {e}")
            return None
            
    def process_post(self, post):
        """處理單篇文章數據 - 只處理基本資料，不獲取詳細內容"""
        try:
            post_id = post.get('id')
            
            # 僅保存基本文章信息到 posts 表
            self.db.insert_post(post)
            logger.info(f"已保存文章基本信息: ID {post_id}, 標題: {post.get('title', '無標題')}")
            
            # 延遲避免請求過快
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
            return True
        except Exception as e:
            logger.error(f"處理文章失敗: {e}")
            return False
            
    def process_post_content(self, post_id):
        """處理單篇文章的詳細內容"""
        try:
            # 獲取文章詳細內容
            post_content = self.fetch_post_content(post_id)
            
            if post_content:
                # 保存文章詳細內容到 post_content 表
                self.db.insert_post_content(post_content)
                logger.info(f"已保存文章詳細內容: ID {post_id}")
                
                # 延遲避免請求過快
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                return True
            return False
        except Exception as e:
            logger.error(f"處理文章詳細內容失敗: {e}")
            return False
            
    def crawl_post(self):
        """爬取文章基本資訊主函數"""
        try:
            # 設置 ScraperAPI
            if not self.setup():
                logger.error("無法設置爬蟲環境")
                return False
            
            # 初始化變數    
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
                    # 保存最後一篇文章的ID，以便下次繼續爬取
                    save_last_id(last_id, self.forum_name)
                    
                logger.info(f"已處理 {posts_count}/{TOTAL_POSTS} 篇文章，最後ID: {last_id}")
                
                # 延遲避免請求過快
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
            return True
        except Exception as e:
            logger.error(f"爬取過程中發生錯誤: {e}")
            # 即使出錯，也要保存最後爬取的ID
            if last_id:
                save_last_id(last_id, self.forum_name)
            return False
        finally:
            self.close()
            
    def crawl_post_content(self, limit=None):
        """爬取文章詳細內容主函數"""
        try:
            # 設置 ScraperAPI
            if not self.setup():
                logger.error("無法設置爬蟲環境")
                return False
            
            # 獲取資料庫中所有需要抓取詳細內容的文章ID
            cursor = self.db.conn.cursor()
            
            # 查詢 posts 表中有記錄但 post_content 表中沒有的文章
            cursor.execute('''
                SELECT p.id FROM posts p
                LEFT JOIN post_content pc ON p.id = pc.post_id
                WHERE pc.post_id IS NULL
                ORDER BY p.id DESC
            ''')
            
            rows = cursor.fetchall()
            total_posts = len(rows)
            
            if limit and limit < total_posts:
                rows = rows[:limit]
                logger.info(f"根據限制條件，將爬取 {limit}/{total_posts} 篇文章詳細內容")
            else:
                logger.info(f"將爬取 {total_posts} 篇文章詳細內容")
            
            processed_count = 0
            
            # 處理每篇文章詳細內容
            for row in rows:
                post_id = row[0]
                
                if self.process_post_content(post_id):
                    processed_count += 1
                    logger.info(f"進度: {processed_count}/{len(rows)}")
                
            logger.info(f"文章詳細內容爬取完成，共處理 {processed_count} 篇")
            return True
            
        except Exception as e:
            logger.error(f"爬取文章詳細內容過程中發生錯誤: {e}")
            return False
        finally:
            self.close()
    
    def crawl(self):
        """保留原方法名稱以保持向後兼容"""
        return self.crawl_post()

# 測試執行
if __name__ == "__main__":
    crawler = ScraperApiCrawler()
    crawler.crawl()
