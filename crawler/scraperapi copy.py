import requests
import urllib3

# 停用不安全的 HTTPS 警告（僅用於開發/測試環境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

proxies = { }

payload = { 'api_key': '874493b63edbe6b44362b48525886d6c', 'url': 'https://www.dcard.tw/service/api/v2/forums/house_purchase/posts?limit=10', 'render': 'true', 'premium': 'true' }

try:
    # 設置 verify=False 來忽略 SSL 憑證驗證
    r = requests.get('https://api.scraperapi.com/', params=payload, proxies=proxies, verify=False)
    print(r.text)
except Exception as e:
    print(f"請求出錯: {e}")
