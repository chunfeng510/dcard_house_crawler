from zenrows import ZenRowsClient
import json
import re
import os
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import time
import sys

# Zenrows functioning url: https://www.dcard.tw/service/api/v2/forums/house_purchase/posts/
# 導入系統設置
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    BASE_URL, FORUM_NAME, HEADERS, POSTS_LIMIT, TOTAL_POSTS,
    DELAY_BETWEEN_REQUESTS, ZENROWS_API_KEY
)
from database.db_manager import DatabaseManager
from utils.helpers import save_last_id, load_last_id

# 設定日誌
logger = logging.getLogger(__name__)

class ZenRowsApiCrawler:
    """使用 ZenRows API 的 Dcard 爬蟲類"""
    
    def __init__(self, api_key=None, forum_name=None, continue_last=True):
        """初始化爬蟲"""
        if api_key is None:
            api_key = ZENROWS_API_KEY
        self.client = ZenRowsClient(api_key)
        self.base_url = BASE_URL # 設定API基本URL
        self.forum_name = forum_name or FORUM_NAME
        self.forum_url = f"{BASE_URL}/forums/{self.forum_name}/posts" # 取得該版下的貼文
        self.save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw_posts')
        os.makedirs(self.save_dir, exist_ok=True)
        self.continue_last = continue_last  # 是否從上次爬取的位置繼續
        
        # 初始化資料庫連接
        self.db = DatabaseManager()
        self.db.connect()
        self.db.initialize_db()
        
    def fetch_post_content(self, post_id):
        """獲取單篇文章內容"""
        try:
            url = f"{self.base_url}/posts/{post_id}"
            params = {
                "js_render": "true",
                "json_response": "true"
            }
            logger.info(f"開始獲取文章內容: {url}")
            response = self.client.get(url, params=params)
            
            if response.status_code == 200:
                json_content = json.loads(response.text)
                if isinstance(json_content, dict) and 'html' in json_content:
                    content_data = json.loads(json_content['html'])
                else:
                    content_data = json_content
                
                # 保存原始數據
                self._save_raw_data(url, content_data)
                
                logger.info(f"成功獲取文章內容: {post_id}")
                return content_data
            else:
                logger.error(f"獲取文章內容失敗，狀態碼: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"獲取文章內容失敗: {e}")
            return None

    def fetch_post(self, limit=POSTS_LIMIT, before=None):
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
                
                logger.info(f"成功獲取 {len(posts_data)} 篇文章")
                return posts_data
            else:
                logger.error("響應中未找到文章數據")
                return []

        except Exception as e:
            logger.error(f"獲取文章列表失敗: {e}")
            self._save_error_response(url, response.text)
            return []

    def fetch_post_comment(self, post_id):
        """獲取文章評論，支持分頁"""
        try:
            # 首先獲取文章的總評論數
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT total_comment_count
                FROM post_content
                WHERE post_id = ?
            ''', (post_id,))
            row = cursor.fetchone()
            if not row:
                logger.error(f"找不到文章 {post_id} 的評論總數信息")
                return None
                
            total_comment_count = row[0]
            if total_comment_count == 0:
                logger.info(f"文章 {post_id} 沒有評論")
                return []
                
            all_comments = []
            after = None
            page = 1
            
            while True:
                # 構建URL和參數
                url = f"{self.base_url}/posts/{post_id}/comments?limit=100"
                params = {
                    "js_render": "true",
                    "json_response": "true"
                }
                
                # 如果有 after 參數，添加到 URL 中
                if after is not None:
                    url += f"&after={after}"

                logger.info(f"開始獲取文章 {post_id} 的第 {page} 頁評論: {url}")
                response = self.client.get(url, params=params)
                
                if response.status_code == 200:
                    json_content = json.loads(response.text)
                    if isinstance(json_content, dict) and 'html' in json_content:
                        comments_data = json.loads(json_content['html'])
                    else:
                        comments_data = json_content
                    
                    if not comments_data:  # 如果返回空列表，說明已經沒有更多評論
                        break
                        
                    # 保存原始數據
                    self._save_raw_data(url, comments_data)
                    
                    all_comments.extend(comments_data)
                    
                    logger.info(f"成功獲取第 {page} 頁評論，目前共 {len(all_comments)}/{total_comment_count} 條")
                    
                    # 如果已經獲取到足夠的評論，或者沒有更多評論，就退出
                    if len(all_comments) >= total_comment_count or len(comments_data) < 100:
                        break
                        
                    # 獲取最後一條評論的樓層號作為下一頁的after參數
                    last_comment = comments_data[-1]
                    after = last_comment.get('floor')
                    
                    page += 1
                    # 在請求之間添加延遲
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                else:
                    logger.error(f"獲取評論失敗，狀態碼: {response.status_code}")
                    if all_comments:  # 如果已經獲取了一些評論，就返回已獲取的部分
                        return all_comments
                    return None
                    
            logger.info(f"完成獲取文章 {post_id} 的所有評論，共 {len(all_comments)} 條")
            return all_comments
            
        except Exception as e:
            logger.error(f"獲取文章評論失敗: {e}")
            return None

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
                self.db.insert_post_content(post_id, post_content)
                logger.info(f"已保存文章詳細內容: ID {post_id}")
                
                # 延遲避免請求過快
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
                return True
            return False
        except Exception as e:
            logger.error(f"處理文章詳細內容失敗: {e}")
            return False

    def process_post_comment(self, post_id, comments_data):
        """處理單篇文章的評論數據"""
        try:
            if not comments_data:
                logger.warning(f"文章 {post_id} 沒有評論數據")
                return False
                
            success_count = 0
            for comment in comments_data:
                try:
                    # 確保評論數據包含必要的文章ID
                    comment['postId'] = post_id
                    
                    # 為可能為空的欄位設置預設值
                    if 'content' not in comment:
                        comment['content'] = None
                        
                    # 保存評論到數據庫
                    self.db.insert_post_comment(comment)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"處理評論時發生錯誤: {e}, 評論ID: {comment.get('id', 'unknown')}")
                    continue
                    
            if success_count > 0:
                logger.info(f"文章 {post_id} 的評論數據處理完成，成功處理 {success_count} 條評論")
                # 延遲避免請求過快
                time.sleep(DELAY_BETWEEN_REQUESTS)
                return True
            else:
                logger.warning(f"文章 {post_id} 的所有評論處理都失敗了")
                return False
            
        except Exception as e:
            logger.error(f"處理文章評論失敗: {e}")
            return False

    def crawl_post(self, total_posts=TOTAL_POSTS):
        """爬取文章基本資訊主函數"""
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
                # 獲取文章列表
                posts = self.fetch_post(before=last_id)
                
                if not posts:
                    logger.warning("沒有更多文章或請求失敗")
                    break
                    
                # 處理每篇文章
                for post in posts:
                    if self.process_post(post):
                        posts_count += 1
                        
                    if posts_count >= total_posts:
                        break
                
                # 記錄最後一篇文章的ID用於分頁
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
            self.close()
            
    def crawl_post_content(self, limit=None):
        """爬取文章詳細內容主函數"""
        try:
            # 獲取資料庫中所有需要抓取詳細內容的文章ID
            cursor = self.db.conn.cursor()
            
            # 查詢 posts 表中有記錄但 post_content 表中沒有的文章
            cursor.execute('''
                SELECT p.id FROM posts p
                LEFT JOIN post_content pc ON p.id = pc.post_id
                WHERE pc.post_id IS NULL
                    and (title like '%貸%' or excerpt like '%貸%')
                    and p.is_deleted = 0
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
    
    def crawl_post_comment(self, limit=None):
        """爬取文章評論主函數"""
        try:
            # 獲取資料庫中需要抓取評論的文章ID
            cursor = self.db.conn.cursor()
            
            # 查詢有內容的文章但還沒有評論的文章
            cursor.execute('''
                SELECT DISTINCT pc.post_id 
                FROM post_content pc
                LEFT JOIN post_comments cm ON pc.post_id = cm.post_id
                WHERE cm.post_id IS NULL and pc.total_comment_count > 0
                and not exists (
                    SELECT 1 
                    FROM posts where is_deleted = 1
                )
                ORDER BY pc.total_comment_count DESC
            ''')
            
            rows = cursor.fetchall()
            total_posts = len(rows)
            
            if limit and limit < total_posts:
                rows = rows[:limit]
                logger.info(f"根據限制條件，將爬取 {limit}/{total_posts} 篇文章的評論")
            else:
                logger.info(f"將爬取 {total_posts} 篇文章的評論")
            
            processed_count = 0
            
            # 處理每篇文章的評論
            for row in rows:
                post_id = row[0]
                
                # 獲取評論數據
                comments_data = self.fetch_post_comment(post_id)
                
                if comments_data and self.process_post_comment(post_id, comments_data):
                    processed_count += 1
                    logger.info(f"進度: {processed_count}/{len(rows)}")
                
            logger.info(f"文章評論爬取完成，共處理 {processed_count} 篇文章的評論")
            return True
            
        except Exception as e:
            logger.error(f"爬取文章評論過程中發生錯誤: {e}")
            return False
        finally:
            self.close()

    def crawl(self, total_posts=TOTAL_POSTS):
        """保留原方法名稱以保持向後兼容"""
        return self.crawl_post_comment(total_posts)
        # return self.crawl_post(total_posts)
        # return self.crawl_post_content(total_posts)
        
    def close(self):
        """關閉數據庫連接"""
        if hasattr(self, 'db') and self.db:
            self.db.close()
            logger.info("已關閉數據庫連接")