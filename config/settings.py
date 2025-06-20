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
# api = bdc809ccb3ef89f494f9c4f06827e85df87a9d12
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

# OpenAI API 設定
OPENAI_API_KEY = "bc8b63256bd342fb999c35eb79780fb8"  # 填入您的 OpenAI API 金鑰
GPT_MODEL = "gpt-4.1"  # 使用的 GPT 模型
GPT_MAX_TOKENS = 1000  # API 回應的最大 token 數量
GPT_TEMPERATURE = 0.3  # API 回應的溫度參數，較低值產生較確定的回覆

# Azure OpenAI 服務設定 (如果使用 Azure OpenAI 服務，請填寫以下設定)
USE_AZURE_OPENAI = True  # 是否使用 Azure OpenAI 服務
AZURE_ENDPOINT_URL = "https://amcchatgpt.openai.azure.com/"  # Azure OpenAI 服務端點 URL
AZURE_API_VERSION = "2024-12-01-preview"  # Azure API 版本
AZURE_DEPLOYMENT_NAME = ""  # Azure OpenAI 部署名稱

# GPT 分析設定
ANALYSIS_BATCH_SIZE = 1000  # 每次分析的文章數量
COMMENT_ANALYSIS_BATCH_SIZE = 1000  # 每次分析的留言數量
MIN_COMMENT_LENGTH = 5  # 最小分析留言長度
MIN_CONFIDENCE_SCORE = 10  # 最小可信度分數，低於此分數的分析結果會被忽略
GPT_API_DELAY = 1  # 每次 API 請求的延遲時間（秒），避免觸發 API 速率限制