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
                    fetch_time DATETIME                    
                )
            ''')
            
            # 創建文章詳細內容表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_content (
                    post_id INTEGER PRIMARY KEY,
                    content TEXT,
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
                    edited_at DATETIME,
                    layout TEXT,
                    annotation TEXT,
                    with_nickname BOOLEAN DEFAULT FALSE,
                    report_reason TEXT,
                    hidden_by_author BOOLEAN DEFAULT FALSE,
                    forum_logo TEXT,
                    quote_count INTEGER DEFAULT 0,
                    links TEXT,
                    identity_id_v3 TEXT,
                    is_moderator BOOLEAN DEFAULT FALSE,
                    suspicious_account BOOLEAN DEFAULT FALSE,
                    enable_private_message BOOLEAN DEFAULT TRUE,
                    enable_nested_comment BOOLEAN DEFAULT TRUE,
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
                    identity_type, fetch_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                datetime.now().isoformat()
            ))
            
            self.conn.commit()
            logger.info(f"成功插入文章: {post_data['title']}")
            return True
        except sqlite3.Error as e:
            logger.error(f"插入文章失敗: {e}")
            self.conn.rollback()
            return False
    
    def insert_post_content(self, post_id, content_data):
        """插入文章詳細內容數據"""
        try:
            cursor = self.conn.cursor()
            
            # 準備 forum_logo 數據
            forum_logo = None
            if content_data.get('forumLogo'):
                forum_logo = str(content_data['forumLogo'])
                
            # 準備 links 數據
            links = None
            if content_data.get('links'):
                links = ','.join(content_data['links'])
                
            cursor.execute('''
                INSERT OR REPLACE INTO post_content (
                    post_id, content, forum_id, forum_name, forum_alias,
                    share_count, pinned, nsfw, department,
                    persona_nickname, topics, media_meta,
                    reactions, total_comment_count, with_images,
                    with_videos, edited, edited_at, layout,
                    with_nickname, report_reason, hidden_by_author,
                    forum_logo, quote_count, links, identity_id_v3,
                    is_moderator, suspicious_account,
                    enable_private_message, enable_nested_comment,
                    raw_data
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            ''', (
                post_id,
                content_data.get('content', ''),
                content_data.get('forumId'),
                content_data.get('forumName'),
                content_data.get('forumAlias'),
                content_data.get('shareCount', 0),
                content_data.get('pinned', False),
                content_data.get('nsfw', False),
                content_data.get('department'),
                content_data.get('personaNickname'),
                ','.join(content_data.get('topics', [])),
                str(content_data.get('mediaMeta', [])),
                str(content_data.get('reactions', [])),
                content_data.get('totalCommentCount', 0),
                content_data.get('withImages', False),
                content_data.get('withVideos', False),
                content_data.get('edited', False),
                content_data.get('editedAt'),
                content_data.get('layout'),
                content_data.get('withNickname', False),
                content_data.get('reportReason', ''),
                content_data.get('hiddenByAuthor', False),
                forum_logo,
                content_data.get('quoteCount', 0),
                links,
                content_data.get('identityIdV3'),
                content_data.get('isModerator', False),
                content_data.get('isSuspiciousAccount', False),
                content_data.get('enablePrivateMessage', True),
                content_data.get('enableNestedComment', True),
                str(content_data)
            ))
            
            self.conn.commit()
            logger.info(f"文章 {post_id} 的詳細內容數據插入成功")
            return True
        except sqlite3.Error as e:
            logger.error(f"文章 {post_id} 的詳細內容數據插入失敗: {e}")
            return False
            
    def close(self):
        """關閉數據庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("數據庫連接已關閉")