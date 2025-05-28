"""
Dcard House Crawler 配置文件
"""

# API 設定
BASE_URL = "https://www.dcard.tw/service/api/v2/posts"
FORUM_NAME = "house"  # 可以更改為其他想爬取的版面
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}

# Selenium 設定
SELENIUM_TIMEOUT = 30  # 秒
SELENIUM_IMPLICIT_WAIT = 10  # 秒

# 資料庫設定
DB_NAME = "dcard_posts.sqlite"
TABLE_NAME = "house_posts"

# 爬蟲設定
POSTS_LIMIT = 100  # 每次請求的文章數量
TOTAL_POSTS = 1000  # 總共要爬取的文章數量，可以調整
DELAY_BETWEEN_REQUESTS = 3  # 每次請求之間的延遲（秒）