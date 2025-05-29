"""
輔助工具函數集
"""
import os
import sys
import logging
import json
from datetime import datetime, timedelta

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'utils.log'),
    encoding='utf-8'
)
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
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"已創建備份: {backup_path}")
            return backup_path
        else:
            logger.warning(f"無法創建備份，文件不存在: {file_path}")
            return None
    except Exception as e:
        logger.error(f"創建備份失敗: {e}")
        return None

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