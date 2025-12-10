import urllib.request
import urllib.error
import os
import time
from datetime import datetime
from dotenv import load_dotenv
# 加载环境变量
load_dotenv()

url = os.getenv("URL")
save_path = r"c:\mihomo\config.yaml"
time_log_path = r"c:\mihomo\updatetime"

# 定义 headers
headers = {
    'User-Agent': 'mihomo'
}

def get_last_update_time():
    """读取上次更新时间"""
    try:
        if os.path.exists(time_log_path):
            with open(time_log_path, 'r') as f:
                timestamp = float(f.read().strip())
                return timestamp
    except:
        pass
    return 0

def save_update_time():
    """保存当前更新时间"""
    try:
        os.makedirs(os.path.dirname(time_log_path), exist_ok=True)
        with open(time_log_path, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"保存时间戳失败: {e}")

def should_update():
    """判断是否需要更新"""
    last_time = get_last_update_time()
    current_time = time.time()
    hours_passed = (current_time - last_time) / 3600
    # 注意：你的注释写的是12小时，但代码里写的是 >= 24
    return hours_passed >= 24

if __name__ == "__main__":
    print("自动更新脚本已启动...")
    while True:
        if should_update():
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # 修改处：在 Request 中添加 headers
                request = urllib.request.Request(url, headers=headers)
                
                print(f"开始下载配置... (User-Agent: {headers['User-Agent']})")
                with urllib.request.urlopen(request, timeout=30) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP 状态码: {response.status}")
                    
                    # 读取数据
                    content = response.read()
                    
                    # 写入文件
                    with open(save_path, 'wb') as f:
                        f.write(content)
                
                save_update_time()
                print(f"配置文件更新成功 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except urllib.error.URLError as e:
                error_msg = f"网络请求失败: {e.reason}"
                print(error_msg)
            except Exception as e:
                error_msg = f"发生错误: {e}"
                print(error_msg)
        
        # 每10分钟检查一次 (600秒)
        time.sleep(600)