"""
Dcard House Crawler 配置文件
"""

# API 設定
"""
API 路徑說明:
- 全部文章: GET /posts
- 看板資訊: GET /forums
- 看板內文章列表: GET /forums/{看板名稱}/posts
- 文章內文: GET /posts/{文章ID}
- 文章內引用連結: GET /posts/{文章ID}/links
- 文章內留言: GET /posts/{文章ID}/comments
"""
BASE_URL = "https://www.dcard.tw/service/api/v2"
FORUM_NAME = "house_purchase"  # 可以更改為其他想爬取的版面
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}


# 資料庫設定
DB_NAME = "dcard_posts.sqlite"
TABLE_NAME = "house_posts"

# 爬蟲設定
POSTS_LIMIT = 100  # 每次請求的文章數量
TOTAL_POSTS = 1000  # 總共要爬取的文章數量，可以調整
DELAY_BETWEEN_REQUESTS = 3  # 每次請求之間的延遲（秒）

# 代理伺服器設定
USE_PROXY = True  # 是否使用代理
PROXY_LIST = [
    "http://auohqwsg.corpnet.auo.com:8080"
]
ROTATE_PROXY = True  # 是否輪換使用不同代理