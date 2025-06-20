#!/usr/bin/env python
"""
Dcard爬蟲主程式入口
"""
import os
import sys
import logging
import argparse
from datetime import datetime

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler.scraperapi import ScraperApiCrawler
from crawler.zenrowsapi import ZenRowsApiCrawler
from database.db_manager import DatabaseManager
from analysis.gpt_analyzer import GPTAnalyzer
from utils.helpers import ensure_directory, create_backup

# 設定日誌目錄
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
ensure_directory(log_dir)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f'main_{datetime.now().strftime("%Y%m%d")}.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(description='Dcard房屋版爬蟲')
    parser.add_argument('--backup', action='store_true', help='在執行前備份資料庫')
    parser.add_argument('--only-verify', action='store_true', help='只驗證環境不執行爬蟲')
    parser.add_argument('--forum', type=str, default='house_purchase', help='指定要爬取的Dcard版面')
    parser.add_argument('--limit', type=int, default=100, help='爬取的文章數量限制')
    parser.add_argument('--analyze', action='store_true', help='執行 GPT 分析')
    parser.add_argument('--only-analyze', action='store_true', help='只執行 GPT 分析，不爬取新文章')
    parser.add_argument('--api-key', type=str, help='OpenAI API 金鑰')
    parser.add_argument('--gpt-model', type=str, default='gpt-3.5-turbo', help='使用的 GPT 模型')
    parser.add_argument('--crawler', type=str, choices=['scraperapi', 'zenrows'], 
                      help='選擇爬蟲方式：scraperapi 或 zenrows')
    parser.add_argument('--scraper-api-key', type=str, help='ScraperAPI 的 API 金鑰')
    parser.add_argument('--no-render', action='store_true', 
                      help='使用 ScraperAPI 時不渲染 JavaScript (更快但可能不完整)')
    return parser.parse_args()

def verify_environment():
    """驗證運行環境"""
    try:
        import requests
        import openai
        
        logger.info(f"Requests版本: {requests.__version__}")
        logger.info(f"OpenAI版本: {openai.__version__}")
        
        # 檢查資料庫目錄
        db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
        ensure_directory(db_dir)
        
        # 嘗試初始化資料庫連接
        db = DatabaseManager()
        if db.connect():
            logger.info("資料庫連接測試成功")
            db.close()
            return True
        else:
            logger.error("資料庫連接測試失敗")
            return False
    except ImportError as e:
        logger.error(f"缺少必要的套件: {e}")
        return False
    except Exception as e:
        logger.error(f"環境驗證失敗: {e}")
        return False

def run_analysis(api_key=None, model=None):
    """執行 GPT 分析"""
    logger.info("開始執行 GPT 分析")
    try:
        analyzer = GPTAnalyzer(api_key=api_key, model=model)
        
        # 分析文章內容
        content_result = analyzer.analyze_post_contents()
        
        # 分析留言
        comment_result = analyzer.analyze_post_comments()
        
        if content_result or comment_result:
            logger.info("GPT 分析任務完成")
            return True
        else:
            logger.warning("GPT 分析任務未完成任何分析")
            return False
    except Exception as e:
        logger.error(f"GPT 分析過程中發生錯誤: {e}")
        return False

def get_crawler(args):
    """根據命令列參數獲取適當的爬蟲實例"""
    if args.crawler == 'scraperapi':
        api_key = args.scraper_api_key or '874493b63edbe6b44362b48525886d6c'  # 預設或自定義的 API 金鑰
        render = not args.no_render  # 默認啟用渲染
        logger.info(f"使用 ScraperAPI 爬蟲模式 (render={render})")
        return ScraperApiCrawler(api_key=api_key, render=render)
    elif args.crawler == 'zenrows':
        api_key = args.scraper_api_key or 'bdc809ccb3ef89f494f9c4f06827e85df87a9d12'  # 預設或自定義的 API 金鑰
        logger.info("使用 ZenRowsAPI 爬蟲模式")
        return ZenRowsApiCrawler(api_key=api_key)
    else:
        logger.error(f"未知的爬蟲類型: {args.crawler}，程式中止")
        sys.exit(1)

def main():
    """主程式入口"""
    logger.info("==== Dcard房屋版爬蟲程式啟動 ====")
    
    # 解析命令列參數
    args = parse_arguments()
    
    # 驗證環境
    if not verify_environment():
        logger.error("環境驗證失敗，程式中止")
        return False
    logger.info("環境驗證通過")
    
    # 如果只是驗證環境，則到此結束
    if args.only_verify:
        logger.info("僅執行環境驗證，程式結束")
        return True
    
    # 如果需要備份，創建備份
    if args.backup:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'dcard_posts.sqlite')
        if os.path.exists(db_path):
            backup_path = create_backup(db_path)
            if backup_path:
                logger.info(f"資料庫備份成功: {backup_path}")
            else:
                logger.warning("資料庫備份失敗")
    
    # 如果只執行分析，則跳過爬蟲
    if args.only_analyze:
        return run_analysis(api_key=args.api_key, model=args.gpt_model)
    
    # 開始爬蟲
    crawl_success = False
    try:
        logger.info("開始爬蟲任務")
        
        # 根據命令列參數選擇爬蟲方式
        crawler = get_crawler(args)
        crawl_success = crawler.crawl()
        
        if crawl_success:
            logger.info("爬蟲任務完成")
        else:
            logger.error("爬蟲任務失敗")
    except Exception as e:
        logger.error(f"爬蟲過程中發生錯誤: {e}")
    
    # 僅在有指定 --analyze 或 --only-analyze 時才進行分析，預設不分析
    if args.analyze or args.only_analyze:
        analysis_success = run_analysis(api_key=args.api_key, model=args.gpt_model)
        logger.info("==== Dcard房屋版爬蟲程式結束 ====")
        return analysis_success if args.only_analyze else (crawl_success and analysis_success)
    else:
        logger.info("==== Dcard房屋版爬蟲程式結束 ====")
        return crawl_success

if __name__ == "__main__":
    sys.exit(0 if main() else 1)