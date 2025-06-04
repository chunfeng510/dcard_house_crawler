# pip install zenrows
from zenrows import ZenRowsClient
import json
import re
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# 創建保存數據的目錄
save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw_posts')
os.makedirs(save_dir, exist_ok=True)

client = ZenRowsClient("3d16f55e44b51fc52353566769dce39bfe0c5c58")
url = "https://www.dcard.tw/service/api/v2/forums/house_purchase/posts"
params = {"js_render":"true", "json_response":"true"}
response = client.get(url, params=params)

# 提取 JSON 字符串
try:
    # 使用正則表達式查找 JSON 數組
    json_str = response.text
    if '"html":' in json_str:
        # 從 response 中提取實際的 JSON 數組
        json_content = json.loads(json_str)
        # 提取 html 字段中的 JSON 字符串
        posts_data = json.loads(json_content['html'])
        
        # 生成帶時間戳和 URL 參數的文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 解析 URL 參數
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        limit = query_params.get('limit', ['unknown'])[0]
        
        # 創建包含 URL 參數的文件名
        filename = f'dcard_posts_limit{limit}_{timestamp}.json'
        filepath = os.path.join(save_dir, filename)
        
        # 在文件開頭添加 URL 信息
        output_data = {
            "url": url,
            "fetch_time": datetime.now().isoformat(),
            "posts": posts_data
        }
        
        # 保存原始響應
        # with open(os.path.join(save_dir, f'raw_response_limit{limit}_{timestamp}.json'), 'w', encoding='utf-8') as f:
        #     json.dump({
        #         "url": url,
        #         "fetch_time": datetime.now().isoformat(),
        #         "response": json_content
        #     }, f, ensure_ascii=False, indent=2)
            
        # 保存解析後的文章數據
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # 打印格式化的結果
        print(f"成功獲取到 {len(posts_data)} 篇文章")
        # print(f"原始響應已保存到: raw_response_limit{limit}_{timestamp}.json")
        print(f"文章數據已保存到: {filename}")
        print(f"請求 URL: {url}")
        print("\n文章預覽:")
        for post in posts_data:
            print(f"標題: {post['title']}")
            print(f"發布時間: {post['createdAt']}")
            print(f"留言數: {post['commentCount']}")
            print("-" * 50)
            
except json.JSONDecodeError as e:
    print(f"JSON 解析錯誤: {e}")
except Exception as e:
    print(f"發生錯誤: {e}")
    # 保存錯誤響應以供調試
    error_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    error_filepath = os.path.join(save_dir, f'error_response_{error_timestamp}.txt')
    with open(error_filepath, 'w', encoding='utf-8') as f:
        f.write(f"URL: {url}\n\n")  # 在錯誤文件中也記錄 URL
        f.write(response.text)
    print(f"錯誤響應已保存到: {error_filepath}")