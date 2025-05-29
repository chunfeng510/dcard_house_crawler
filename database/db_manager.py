"""
資料庫管理模組
"""
import sqlite3
import os
import sys
from datetime import datetime
import logging

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_NAME, TABLE_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'database.log'),
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """管理 SQLite 資料庫的類別"""
    
    def __init__(self, db_name=DB_NAME):
        """初始化資料庫連接"""
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', db_name)
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """連接到資料庫"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            logger.info(f"成功連接到資料庫: {self.db_path}")
            return True
        except sqlite3.Error as e:
            logger.error(f"資料庫連接失敗: {e}")
            return False
            
    def initialize_db(self):
        """初始化資料庫表格"""
        if not self.conn:
            self.connect()
            
        try:
            self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                content TEXT,
                post_date TEXT,
                created_at TEXT,
                relevance_score INTEGER DEFAULT NULL,
                structured_data TEXT DEFAULT NULL,
                analyzed_at TEXT DEFAULT NULL
            )
            ''')
            self.conn.commit()
            logger.info(f"成功初始化資料表: {TABLE_NAME}")
            return True
        except sqlite3.Error as e:
            logger.error(f"初始化資料表失敗: {e}")
            return False
    
    def insert_post(self, title, content, post_date):
        """插入一篇文章到資料庫"""
        if not self.conn:
            self.connect()
            
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute(
                f"INSERT INTO {TABLE_NAME} (title, content, post_date, created_at) VALUES (?, ?, ?, ?)",
                (title, content, post_date, current_time)
            )
            self.conn.commit()
            logger.info(f"已添加文章: {title}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"文章已存在: {title}")
            return False
        except sqlite3.Error as e:
            logger.error(f"添加文章失敗: {e}")
            return False
    
    def get_all_posts(self):
        """獲取所有文章"""
        if not self.conn:
            self.connect()
            
        try:
            self.cursor.execute(f"SELECT * FROM {TABLE_NAME}")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"獲取文章失敗: {e}")
            return []
    
    def get_posts_for_analysis(self):
        """獲取尚未分析的文章"""
        if not self.conn:
            self.connect()
            
        try:
            self.cursor.execute(f"""
                SELECT id, title, content 
                FROM {TABLE_NAME} 
                WHERE analyzed_at IS NULL
                AND content IS NOT NULL
            """)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"獲取待分析文章失敗: {e}")
            return []
    
    def update_post_analysis(self, post_id, relevance_score, structured_data):
        """更新文章的分析結果"""
        if not self.conn:
            self.connect()
            
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.cursor.execute(
                f"""
                UPDATE {TABLE_NAME} 
                SET relevance_score = ?, structured_data = ?, analyzed_at = ? 
                WHERE id = ?
                """,
                (relevance_score, structured_data, current_time, post_id)
            )
            self.conn.commit()
            logger.info(f"已更新文章ID {post_id} 的分析結果")
            return True
        except sqlite3.Error as e:
            logger.error(f"更新文章分析結果失敗: {e}")
            return False
    
    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("資料庫連接已關閉")

# 測試程式碼
if __name__ == "__main__":
    db = DatabaseManager()
    db.connect()
    db.initialize_db()
    db.close()