"""
輔助工具函數集
"""
import os
import sys
import logging
import json
import time
import shutil
import functools
from datetime import datetime, timedelta
from typing import Callable, Any, Optional

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 設定日誌
logger = logging.getLogger(__name__)

def ensure_directory(directory_path):
    """確保目錄存在，不存在則創建"""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logger.info(f"已創建目錄: {directory_path}")
            return True
        except OSError as e:
            logger.error(f"無法創建目錄 {directory_path}: {e}")
            return False
    return True

def save_json(data, file_path):
    """將數據保存為JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"數據已保存到: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存JSON文件失敗: {e}")
        return False

def load_json(file_path):
    """從JSON文件加載數據"""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"已加載數據從: {file_path}")
        return data
    except Exception as e:
        logger.error(f"加載JSON文件失敗: {e}")
        return None

def format_timestamp(timestamp_str):
    """格式化時間戳為標準格式"""
    try:
        # 處理ISO格式的時間
        if 'T' in timestamp_str and ('Z' in timestamp_str or '+' in timestamp_str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
            
        # 處理Unix時間戳
        if timestamp_str.isdigit():
            dt = datetime.fromtimestamp(int(timestamp_str))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
            
        # 其他格式嘗試直接解析
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        logger.error(f"日期格式化失敗: {e}")
        return timestamp_str
        
def create_backup(file_path):
    """創建文件備份"""
    try:
        if os.path.exists(file_path):
            backup_path = f"{file_path}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
            shutil.copy2(file_path, backup_path)
            logger.info(f"已創建備份: {backup_path}")
            return backup_path
        else:
            logger.warning(f"無法創建備份，文件不存在: {file_path}")
            return None
    except Exception as e:
        logger.error(f"創建備份失敗: {e}")
        return None

def save_last_id(last_id, forum_name=None):
    """保存最後爬取的文章 ID"""
    try:
        # 設置保存路徑
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        ensure_directory(data_dir)
        
        # 創建或讀取現有的狀態檔案
        state_path = os.path.join(data_dir, 'crawler_state.json')
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                state_data = {}
        else:
            state_data = {}
        
        # 更新狀態
        forum_key = forum_name or 'default'
        if forum_key not in state_data:
            state_data[forum_key] = {}
            
        state_data[forum_key]['last_id'] = last_id
        state_data[forum_key]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存狀態
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"成功保存最後爬取的文章 ID: {last_id} (版面: {forum_key})")
        return True
    except Exception as e:
        logger.error(f"保存最後爬取的文章 ID 失敗: {e}")
        return False

def load_last_id(forum_name=None):
    """讀取最後爬取的文章 ID"""
    try:
        # 設置保存路徑
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        state_path = os.path.join(data_dir, 'crawler_state.json')
        
        if not os.path.exists(state_path):
            logger.warning(f"找不到狀態檔案: {state_path}")
            return None
            
        # 讀取狀態
        with open(state_path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
            
        # 獲取特定論壇的最後 ID
        forum_key = forum_name or 'default'
        if forum_key not in state_data or 'last_id' not in state_data[forum_key]:
            logger.warning(f"找不到版面 {forum_key} 的最後爬取 ID")
            return None
            
        last_id = state_data[forum_key]['last_id']
        updated_at = state_data[forum_key].get('updated_at', '未知時間')
        logger.info(f"讀取最後爬取的文章 ID: {last_id} (版面: {forum_key}, 更新時間: {updated_at})")
        return last_id
    except Exception as e:
        logger.error(f"讀取最後爬取的文章 ID 失敗: {e}")
        return None

def retry(
    max_tries: int = 3, 
    delay: float = 1.0, 
    backoff_factor: float = 2.0, 
    exceptions: tuple = (Exception,), 
    on_retry: Optional[Callable] = None
) -> Callable:
    """
    重試裝飾器，當函數拋出指定的異常時進行重試
    
    參數:
        max_tries: 最大重試次數
        delay: 初始延遲時間（秒）
        backoff_factor: 延遲時間的增長因子
        exceptions: 需要重試的異常類型
        on_retry: 重試前調用的函數，接收異常和當前重試次數作為參數
        
    返回:
        裝飾後的函數
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            mtries, mdelay = max_tries, delay
            last_exception = None
            
            # 嘗試調用函數
            while mtries > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    mtries -= 1
                    last_exception = e
                    
                    if mtries <= 0:
                        break
                        
                    # 記錄重試信息
                    logger.warning(f"{func.__name__} 失敗，將在 {mdelay:.2f} 秒後重試，剩餘 {mtries} 次重試機會。錯誤: {e}")
                    
                    # 調用重試回調函數
                    if on_retry:
                        on_retry(e, max_tries - mtries)
                        
                    # 等待一段時間再重試
                    time.sleep(mdelay)
                    
                    # 增加延遲時間
                    mdelay *= backoff_factor
                    
            # 抛出最後的異常
            raise last_exception
            
        return wrapper
    return decorator

# 測試程式碼
if __name__ == "__main__":
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test')
    ensure_directory(test_dir)
    
    test_data = {"test": "data", "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    test_file = os.path.join(test_dir, 'test.json')
    
    save_json(test_data, test_file)
    loaded_data = load_json(test_file)
    
    print("Test data:", loaded_data)
    print("Formatted date:", format_timestamp('2023-05-28T12:34:56Z'))