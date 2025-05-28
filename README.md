# dcard_house_crawler

### Project Specification.
#### Description: 
I want to create a crawler to collect the post of a website, the base url is : https://www.dcard.tw/service/api/v2/posts

But the the above api has a cloudflare checker, so i plan to use 'Selenium' to operate it without being block.

After scrap all the post, store them to a .sqlite db file
With the schemas:
1. Title (PK)
1. Content
1. Post date
1. Relevance score (與「房貸」相關程度)
1. Structured data (結構化資訊)
And i will then do some ETL with the .sqlite file. (TBD)

#### Back-end Language:
- Python

#### Front-end Language:
*TBD*

## 專案架構與實作計畫

### 專案架構
```
dcard_house_crawler/
├── config/                # 配置目錄
│   └── settings.py        # 配置文件
├── crawler/               # 爬蟲模組
│   └── dcard_crawler.py   # Dcard爬蟲實現
├── database/              # 資料庫模組
│   └── db_manager.py      # SQLite資料庫管理器
├── analysis/              # 分析模組
│   └── gpt_analyzer.py    # GPT文章分析實現
├── logs/                  # 日誌目錄
├── utils/                 # 工具模組
│   └── helpers.py         # 輔助函數
├── main.py                # 主程式入口
├── README.md              # 專案說明
└── requirements.txt       # 依賴套件清單
```

### 功能模組說明

1. **配置模組** (`config/settings.py`)：
   - 包含爬蟲所需的所有設定，如API URLs、瀏覽器設定、資料庫設定等

2. **資料庫模組** (`database/db_manager.py`)：
   - 負責處理SQLite數據庫操作
   - 提供資料表創建、文章插入和查詢功能

3. **爬蟲模組** (`crawler/dcard_crawler.py`)：
   - 使用Selenium繞過Cloudflare保護
   - 實現爬取Dcard文章的核心邏輯
   - 包含獲取文章清單和詳細內容的功能

4. **分析模組** (`analysis/gpt_analyzer.py`):
   - 使用 GPT 模型分析爬取的文章內容
   - 評估文章與「房貸」主題的相關程度 (0-100分)
   - 從文章中提取結構化資訊 (房貸金額、利率、年限等)

5. **工具模組** (`utils/helpers.py`)：
   - 提供輔助函數，包括檔案操作、日期格式化、目錄管理等

6. **主程式** (`main.py`)：
   - 命令行入口點，包含參數解析
   - 環境驗證功能
   - 執行爬蟲並處理錯誤
   - 執行 GPT 分析

### 執行步驟

1. **建立虛擬環境並安裝依賴**：
   ```bash
   # 建立虛擬環境
   python -m venv venv
   
   # 在 Windows 上啟動虛擬環境
   .\venv\Scripts\activate
   
   # 在 Linux/Mac 上啟動虛擬環境
   # source venv/bin/activate
   
   # 安裝依賴套件
   pip install -r requirements.txt
   ```

2. **安裝Chrome瀏覽器及WebDriver**：
   確保已安裝Chrome瀏覽器，Selenium將自動管理WebDriver。

3. **執行環境檢查**：
   ```bash
   python main.py --only-verify
   ```

4. **執行爬蟲**：
   ```bash
   python main.py
   ```
   
   附加選項：
   - `--backup`：執行前備份資料庫
   - `--forum <版名>`：爬取指定的Dcard版面（默認為house）
   - `--limit <數量>`：限制爬取的文章數量
   
5. **執行 GPT 分析**：
   ```bash
   # 爬取並分析
   python main.py --analyze --api-key "您的OpenAI API金鑰"
   
   # 只分析不爬取
   python main.py --only-analyze --api-key "您的OpenAI API金鑰"
   ```
   
   附加選項：
   - `--api-key <金鑰>`：OpenAI API 金鑰（也可以通過環境變數 OPENAI_API_KEY 設定）
   - `--gpt-model <模型>`：使用的 GPT 模型（預設為 gpt-3.5-turbo）

### 注意事項

1. **Cloudflare 繞過方案**：
   - 使用Selenium模擬真實瀏覽器行為來繞過Cloudflare保護
   - 第一次執行時，瀏覽器會彈出視窗，建議不要使用headless模式

2. **爬蟲速度控制**：
   - 在`config/settings.py`中設定了請求間隔參數(`DELAY_BETWEEN_REQUESTS`)
   - 請根據實際情況調整，避免IP被封鎖

3. **日誌系統**：
   - 所有操作都有詳細日誌記錄在`logs`目錄
   - 可以從日誌中查看爬蟲運行狀態和錯誤信息

4. **GPT 分析**：
   - 需要 OpenAI API 金鑰
   - API 呼叫會產生費用，建議設置 TOTAL_POSTS 參數控制分析數量
   - 每次分析會間隔 1 秒以避免 API 速率限制

### GPT 分析輸出
GPT 分析功能會輸出兩個主要結果：

1. **相關度分數** (`relevance_score`):
   - 0-100 的分數表示文章與「房貸」主題的相關程度
   - 0分表示完全無關，100分表示非常相關

2. **結構化資訊** (`structured_data`):
   包含以下結構化資訊（若文章中有提及）：
   - 房貸金額
   - 房貸利率
   - 貸款年限
   - 貸款成數
   - 月付金額
   - 提到的銀行名稱列表

### 可能的後續優化

1. **增加代理IP功能**：
   - 集成代理IP池，避免單一IP頻繁請求被封鎖

2. **多線程或異步支持**：
   - 透過多線程或異步處理提高爬蟲效率

3. **資料分析模塊**：
   - 擴展分析功能，如熱點話題識別、價格趨勢分析等
   - 加入視覺化分析結果的功能

4. **Web界面**：
   - 開發簡單的Web界面來監控爬蟲運行狀態和查看數據
   - 提供分析結果的視覺化展示


