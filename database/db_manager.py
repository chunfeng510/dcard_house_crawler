"""
數據庫管理模組 - 處理 Dcard 文章數據的存儲和檢索
"""
import os
import logging
import sqlite3
from datetime import datetime

# 設定日誌
logger = logging.getLogger(__name__)

class DatabaseManager:
    """數據庫管理類"""
    
    def __init__(self, db_path=None):
        """初始化數據庫連接"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dcard_posts.sqlite')
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """建立數據庫連接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info("數據庫連接成功")
            return True
        except sqlite3.Error as e:
            logger.error(f"數據庫連接失敗: {e}")
            return False
            
    def initialize_db(self):
        """初始化數據庫表"""
        try:
            cursor = self.conn.cursor()
            
            # 創建文章主表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    excerpt TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME,
                    comment_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    collection_count INTEGER DEFAULT 0,                                        
                    gender TEXT,
                    school TEXT,
                    is_anonymous_school BOOLEAN,
                    is_anonymous_department BOOLEAN,
                    identity_type TEXT,
                    content TEXT,
                    fetch_time DATETIME                    
                )
            ''')
            
            # 創建文章詳細內容表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_content (
                    post_id INTEGER PRIMARY KEY,
                    forum_id TEXT,
                    forum_name TEXT,
                    forum_alias TEXT,
                    share_count INTEGER DEFAULT 0,
                    pinned BOOLEAN DEFAULT FALSE,
                    nsfw BOOLEAN DEFAULT FALSE,
                    department TEXT,
                    persona_nickname TEXT,
                    topics TEXT,
                    categories TEXT,
                    media_meta TEXT,
                    reactions TEXT,
                    total_comment_count INTEGER DEFAULT 0,
                    with_images BOOLEAN DEFAULT FALSE,
                    with_videos BOOLEAN DEFAULT FALSE,
                    edited BOOLEAN DEFAULT FALSE,
                    layout TEXT,
                    annotation TEXT,
                    raw_data TEXT,
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                )
            ''')
            
            self.conn.commit()
            logger.info("數據庫表初始化成功")
            return True
        except sqlite3.Error as e:
            logger.error(f"數據庫表初始化失敗: {e}")
            return False
            
    def insert_post(self, post_data):
        """插入文章數據"""
        try:
            cursor = self.conn.cursor()
            
            # 插入主要文章數據
            cursor.execute('''
                INSERT OR REPLACE INTO posts (
                    id, title, excerpt, created_at, updated_at,
                    comment_count, like_count, collection_count,
                    gender, school, is_anonymous_school, is_anonymous_department,
                    identity_type, content, fetch_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data['id'],
                post_data['title'],
                post_data.get('excerpt', ''),
                post_data['createdAt'],
                post_data['updatedAt'],
                post_data['commentCount'],
                post_data['likeCount'],
                post_data['collectionCount'],
                post_data.get('gender', ''),
                post_data.get('school', ''),
                post_data['anonymousSchool'],
                post_data['anonymousDepartment'],
                post_data['identityType'],
                post_data.get('content', ''),
                datetime.now().isoformat()
            ))
            
            self.conn.commit()
            logger.info(f"成功插入文章: {post_data['title']}")
            return True
        except sqlite3.Error as e:
            logger.error(f"插入文章失敗: {e}")
            self.conn.rollback()
            return False
    
    def insert_post_content(self, post_content_data):
        """插入文章詳細內容數據"""
        try:
            import json
            cursor = self.conn.cursor()
            
            # 將列表或字典類型的字段轉換為 JSON 字符串
            topics = json.dumps(post_content_data.get('topics', []), ensure_ascii=False)
            categories = json.dumps(post_content_data.get('categories', []), ensure_ascii=False)
            media_meta = json.dumps(post_content_data.get('mediaMeta', []), ensure_ascii=False)
            reactions = json.dumps(post_content_data.get('reactions', []), ensure_ascii=False)
            annotation = json.dumps(post_content_data.get('meta', {}).get('annotation', {}), ensure_ascii=False)
            
            # 插入文章詳細內容
            cursor.execute('''
                INSERT OR REPLACE INTO post_content (
                    post_id, forum_id, forum_name, forum_alias, share_count,
                    pinned, nsfw, department, persona_nickname, topics,
                    categories, media_meta, reactions, total_comment_count, 
                    with_images, with_videos, edited, layout, annotation, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_content_data['id'],
                post_content_data.get('forumId', ''),
                post_content_data.get('forumName', ''),
                post_content_data.get('forumAlias', ''),
                post_content_data.get('shareCount', 0),
                post_content_data.get('pinned', False),
                post_content_data.get('nsfw', False),
                post_content_data.get('department', ''),
                post_content_data.get('personaNickname', ''),
                topics,
                categories,
                media_meta,
                reactions,
                post_content_data.get('totalCommentCount', 0),
                post_content_data.get('withImages', False),
                post_content_data.get('withVideos', False),
                post_content_data.get('edited', False),
                post_content_data.get('layout', ''),
                annotation,
                json.dumps(post_content_data, ensure_ascii=False)  # 儲存完整原始數據
            ))
            
            self.conn.commit()
            logger.info(f"成功插入文章詳細內容: {post_content_data['id']}")
            return True
        except sqlite3.Error as e:
            logger.error(f"插入文章詳細內容失敗: {e}")
            self.conn.rollback()
            return False
            
    def close(self):
        """關閉數據庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("數據庫連接已關閉")