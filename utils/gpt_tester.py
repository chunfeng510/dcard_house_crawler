"""
GPT API 連接測試工具
用於測試 OpenAI API 金鑰是否有效，並可以進行簡單對話
支持 OpenAI v1.0+ 和 Azure OpenAI
"""
import os
import sys
import logging
from datetime import datetime
from openai import OpenAI, AzureOpenAI

# 將專案根目錄加入系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 設定日誌
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f'gpt_test_{datetime.now().strftime("%Y%m%d")}.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GPTTester:
    """用於測試 GPT API 連接的類別"""
    
    def __init__(self, api_key=None, model="gpt-3.5-turbo", endpoint_url=None, api_version="2024-12-01-preview", deployment=None):
        """初始化 GPT 測試器"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未提供 OpenAI API 金鑰。請通過參數提供或設定環境變數 OPENAI_API_KEY")
        
        self.model = model
        self.endpoint_url = endpoint_url or os.environ.get("ENDPOINT_URL")
        self.deployment = deployment or os.environ.get("AZURE_DEPLOYMENT_NAME", model)
        self.api_version = api_version
        
        # 根據是否有端點 URL 來初始化客戶端
        if self.endpoint_url and "azure" in self.endpoint_url:
            logger.info(f"使用 Azure OpenAI API，端點: {self.endpoint_url}")
            print(f"使用 Azure OpenAI API，端點: {self.endpoint_url}")
            self.client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=self.endpoint_url,
                api_key=self.api_key
            )
            self.is_azure = True
        else:
            logger.info("使用標準 OpenAI API")
            print("使用標準 OpenAI API")
            self.client = OpenAI(api_key=self.api_key)
            self.is_azure = False
        
        logger.info(f"初始化 GPT 測試器，使用模型: {model}")
    
    def test_connection(self):
        """測試 API 連接是否正常"""
        try:
            if self.is_azure:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello, can you hear me?"}
                    ],
                    max_tokens=50,
                    model=self.deployment
                )
            else:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Hello, can you hear me?"}
                    ],
                    max_tokens=50,
                    model=self.model
                )
            
            message = response.choices[0].message.content
            logger.info(f"API 連接測試成功!")
            logger.info(f"GPT 回應: {message}")
            return True, message
        
        except Exception as e:
            logger.error(f"API 連接測試失敗: {str(e)}")
            return False, str(e)
    
    def chat(self):
        """與 GPT 進行簡單的對話"""
        logger.info("開始與 GPT 聊天 (輸入 'exit' 或 'quit' 結束對話)")
        
        messages = [{"role": "system", "content": "你是一個友善的助手，請用中文回答問題。"}]
        
        try:
            while True:
                user_input = input("\n您: ")
                
                if user_input.lower() in ["exit", "quit", "退出", "離開"]:
                    logger.info("結束對話")
                    break
                
                messages.append({"role": "user", "content": user_input})
                
                try:
                    if self.is_azure:
                        response = self.client.chat.completions.create(
                            messages=messages,
                            max_tokens=1000,
                            model=self.deployment
                        )
                    else:
                        response = self.client.chat.completions.create(
                            messages=messages,
                            max_tokens=1000,
                            model=self.model
                        )
                    
                    assistant_message = response.choices[0].message.content
                    messages.append({"role": "assistant", "content": assistant_message})
                    
                    print(f"\nGPT: {assistant_message}")
                    
                except Exception as e:
                    logger.error(f"對話過程中發生錯誤: {str(e)}")
                    print(f"\n錯誤: {str(e)}")
                    
        except KeyboardInterrupt:
            logger.info("用戶中斷對話")
            print("\n對話已結束")

def main():
    """主函數"""
    print("===== GPT API 連接測試工具 =====")
    
    # 嘗試從環境變數獲取 API 金鑰與端點 URL
    api_key = os.environ.get("OPENAI_API_KEY")
    endpoint_url = os.environ.get("ENDPOINT_URL")
    
    # 如果環境變數中沒有，則從用戶輸入獲取
    if not api_key:
        api_key = input("請輸入您的 OpenAI API 金鑰: ")
    
    # 詢問是否使用自訂端點
    use_custom_endpoint = input("是否使用自訂端點 URL? (y/n): ").lower()
    if use_custom_endpoint in ["y", "yes", "是"] and not endpoint_url:
        endpoint_url = input("請輸入端點 URL (例如 https://xxx.openai.azure.com/): ")
    
    # 如果使用 Azure OpenAI，詢問部署名稱
    deployment = None
    if endpoint_url and "azure" in endpoint_url:
        deployment = os.environ.get("AZURE_DEPLOYMENT_NAME")
        if not deployment:
            deployment = input("請輸入 Azure OpenAI 部署名稱 (默認使用模型名稱作為部署名稱): ")
    
    # 測試連接
    try:
        tester = GPTTester(api_key=api_key, endpoint_url=endpoint_url, deployment=deployment)
        
        print("\n正在測試 API 連接...\n")
        success, message = tester.test_connection()
        
        if success:
            print(f"✅ API 連接測試成功!")
            print(f"GPT 回應: {message}\n")
            
            # 詢問是否進行對話測試
            chat_test = input("是否要進行對話測試? (y/n): ").lower()
            if chat_test in ["y", "yes", "是"]:
                tester.chat()
        else:
            print(f"❌ API 連接測試失敗: {message}")
            
    except Exception as e:
        print(f"發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()