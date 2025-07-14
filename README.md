# dcard_house_crawler

### Project Specification.
#### Description: 
I want to create a crawler to collect the post of a website, the base url is : https://www.dcard.tw/service/api/v2/posts

But the the above api has a cloudflare checker, so i am using 'Zenrows' service as a intermediate environment to bypass.

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
│   ├── base_crawler.py    # 爬蟲基礎類別
│   ├── scraperapi.py      # ScraperAPI爬蟲實現
│   └── zenrowsapi.py      # ZenRows API爬蟲實現
├── database/              # 資料庫模組
│   └── db_manager.py      # SQLite資料庫管理器
├── analysis/              # 分析模組
│   └── gpt_analyzer.py    # GPT文章分析實現
├── logs/                  # 日誌目錄
├── utils/                 # 工具模組
│   └── helpers.py         # 輔助函數
│   └── gpt_tester.py      # GPT API 測試工具
├── main.py                # 主程式入口
├── README.md              # 專案說明
└── requirements.txt       # 依賴套件清單
```

### 功能模組說明

1. **配置模組** (`config/settings.py`)：
   - 包含爬蟲所需的所有設定，如API URLs、HTTP請求頭、資料庫設定等
   - 包含代理伺服器的配置選項
   - 可調整爬蟲延遲時間和重試機制參數

2. **資料庫模組** (`database/db_manager.py`)：
   - 負責處理SQLite數據庫操作
   - 提供資料表創建、文章插入和查詢功能
   - 支援文章詳細內容和評論資料的存儲
   - 實作資料庫自動備份功能

3. **爬蟲模組**：
   - `crawler/base_crawler.py`：定義爬蟲基礎類別，提供共用的方法和介面
   - `crawler/scraperapi.py`：使用ScraperAPI服務爬取內容，可用於繞過防爬蟲保護
   - `crawler/zenrowsapi.py`：使用ZenRows API服務爬取內容，提供強大的JS渲染和防爬蟲繞過功能
   - 支援續爬功能，記錄最後爬取的文章ID

4. **分析模組** (`analysis/gpt_analyzer.py`):
   - 使用 GPT 模型分析爬取的文章內容
   - 評估文章與「房貸」主題的相關程度 (0-100分)
   - 從文章中提取結構化資訊 (房貸金額、利率、年限等)

5. **工具模組**：
   - `utils/helpers.py`：提供輔助函數，包括檔案操作、日期格式化、目錄管理等
   - `utils/gpt_tester.py`：測試 GPT API 連接工具，支援 OpenAI 和 Azure OpenAI 服務
   - 新增爬蟲狀態管理功能，追蹤不同論壇的爬取進度

6. **主程式** (`main.py`)：
   - 命令行入口點，包含參數解析
   - 環境驗證功能
   - 支援選擇不同的爬蟲方式
   - 執行爬蟲並處理錯誤
   - 執行 GPT 分析
   - 支援多種運行模式和自訂參數

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

3. **執行環境檢查**：
   ```bash
   python main.py --only-verify
   ```

4. **執行爬蟲**：
   ```bash
   
   # 使用 ScraperAPI 爬蟲
   python main.py --crawler scraperapi
   
   # 使用 ScraperAPI 爬蟲並指定自己的 API 金鑰
   python main.py --crawler scraperapi --scraper-api-key YOUR_API_KEY
   
   # 使用 ZenRows API 爬蟲
   python main.py --crawler zenrows
   
   # 使用 ZenRows API 爬蟲並指定自己的 API 金鑰
   python main.py --crawler zenrows --zenrows-api-key YOUR_API_KEY
   ```
   
   附加選項：
   - `--backup`：執行前備份資料庫
   - `--forum <版名>`：爬取指定的Dcard版面（默認為house_purchase）
   - `--limit <數量>`：限制爬取的文章數量
   - `--last-id <ID>`：從指定的文章ID開始爬取
   - `--store-comments`：同時爬取並儲存文章評論
   - `--crawler <爬蟲類型>`：選擇使用的爬蟲類型（scraperapi 或 zenrows）
   - `--scraper-api-key <API金鑰>`：ScraperAPI 的 API 金鑰
   - `--zenrows-api-key <API金鑰>`：ZenRows 的 API 金鑰
   - `--no-render`：使用 ScraperAPI 時不渲染 JavaScript (更快但可能不完整)
   - `--retry <次數>`：設定請求失敗時的重試次數（默認3次）
   
5. **執行 GPT 分析**：
   ```bash
   # 爬取並分析
   python main.py --analyze --api-key "您的OpenAI API金鑰"
   
   # 只分析不爬取
   python main.py --only-analyze --api-key "您的OpenAI API金鑰"
   
   # 批次分析多篇文章
   python main.py --only-analyze --batch-size 10 --api-key "您的OpenAI API金鑰"
   ```
   
   附加選項：
   - `--api-key <金鑰>`：OpenAI API 金鑰（也可以通過環境變數 OPENAI_API_KEY 設定）
   - `--gpt-model <模型>`：使用的 GPT 模型（預設為 gpt-3.5-turbo）
   - `--endpoint-url <端點URL>`：使用 Azure OpenAI 服務時的端點 URL
   - `--api-version <版本>`：使用 Azure OpenAI 服務時的API版本
   - `--deployment-name <部署名稱>`：使用 Azure OpenAI 服務時的部署名稱
   - `--batch-size <數量>`：批次分析的文章數量
   - `--min-score <分數>`：過濾低於指定相關度分數的文章

### 注意事項

1. **爬蟲方式選擇**：
   - **ScraperAPI 爬蟲**：使用付費 API 服務，速度較快，無需自行管理 IP 和瀏覽器，但有使用配額限制
   - **ZenRows API 爬蟲**：提供強大的 JavaScript 渲染和防爬蟲繞過功能，支援自動處理 Cloudflare 保護，具有良好的穩定性和高效能

2. **代理伺服器功能**：
   - 在`config/settings.py`中可配置代理伺服器，支援多個代理和輪換策略
   - 適用於經常爬取大量數據的情境，可避免 IP 被封鎖

3. **Cloudflare 繞過方案**：
   - 使用Zenrows 服務來爬取具有cloudflare保護的網站

4. **爬蟲速度控制**：
   - 在`config/settings.py`中設定了請求間隔參數(`DELAY_BETWEEN_REQUESTS`)
   - 請根據實際情況調整，避免IP被封鎖
   - 支援自適應延遲功能，依據伺服器回應時間動態調整

5. **日誌系統**：
   - 所有操作都有詳細日誌記錄在`logs`目錄
   - 可以從日誌中查看爬蟲運行狀態和錯誤信息
   - 支援按日期自動分割日誌文件

6. **GPT 分析**：
   - 需要 OpenAI API 金鑰
   - 支持標準 OpenAI API 和 Azure OpenAI 服務
   - API 呼叫會產生費用，建議設置 TOTAL_POSTS 參數控制分析數量
   - 每次分析會間隔 1 秒以避免 API 速率限制
   - 可根據相關度分數過濾分析結果

7. **增量爬取**：
   - 系統會記錄最後爬取的文章ID，支援從上次中斷處繼續爬取
   - 可通過 `--last-id` 參數手動指定起始爬取點

8. **評論資料**：
   - 可通過 `--store-comments` 參數同時爬取和存儲文章評論
   - 評論資料以JSON格式存儲，支援後續分析

### GPT 分析輸出
GPT 分析功能會輸出兩個主要結果：

1. **相關度分數** (`relevance_score`):
   - 0-100 的分數表示文章與「房貸」主題的相關程度
   - 0分表示完全無關，100分表示非常相關

2. **結構化資訊** (`structured_data`):
   包含以下結構化資訊（若文章中有提及）：
   - 房屋總價: 房屋、建案的總價
   - 房貸金額: 向銀行申貸的金額
   - 房貸利率: 貸款的利息率
   - 貸款年限
   - 貸款成數
   - 月付金額
   - 寬限期資訊
   - 提到的銀行名稱列表
   - 貸款類型（如新青安、一般房貸等）
   - 相關房市區域

### 可能的後續優化

1. **增強代理IP功能**：
   - 增加自動檢測代理可用性
   - 支援更多類型的代理（如 SOCKS）

2. **多線程或異步支持**：
   - 透過多線程或異步處理提高爬蟲效率
   - 實現文章與評論的並行爬取

3. **資料分析模塊**：
   - 擴展分析功能，如熱點話題識別、價格趨勢分析等
   - 加入視覺化分析結果的功能
   - 支援情感分析和主題分類

4. **Web界面**：
   - 開發簡單的Web界面來監控爬蟲運行狀態和查看數據
   - 提供分析結果的視覺化展示
   - 加入儀表板功能，顯示房貸相關趨勢變化
   
5. **更多爬蟲方式**:
   - 添加 CloudScraper 模式
   - 實現輪換使用者代理的功能
   - 支援更多來源網站的爬取


