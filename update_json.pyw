import requests
import os
import time
import json
import subprocess
import ctypes
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置信息
url = os.getenv("URL")
user_agent = os.getenv("USER_AGENT", "sing-box_pc")
# [修改] 你的服务名称 (必须与 Windows 服务列表中显示的一致)
SERVICE_NAME = "Sing-box" 

save_path = r"c:\sing-box\config.json"
time_log_path = r"c:\sing-box\updatetime"

headers = {"User-Agent": user_agent}

def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_last_update_time():
    """读取上次更新时间"""
    try:
        if os.path.exists(time_log_path):
            with open(time_log_path, "r") as f:
                content = f.read().strip()
                if content:
                    return float(content)
    except Exception:
        pass
    return 0

def save_update_time():
    """保存当前更新时间"""
    try:
        os.makedirs(os.path.dirname(time_log_path), exist_ok=True)
        with open(time_log_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"保存时间戳失败: {e}")

def should_update():
    """判断是否需要更新"""
    last_time = get_last_update_time()
    current_time = time.time()
    hours_passed = (current_time - last_time) / 3600
    
    if last_time == 0:
        return True
    
    # 这里设置为 12 小时检查一次，你可以根据需要修改
    return hours_passed >= 12

def restart_service():
    """重启 Sing-box 服务"""
    print(f"正在尝试重启服务: {SERVICE_NAME} ...")
    try:
        # 1. 停止服务
        # check=False 允许命令失败(例如服务本身就没在运行)，不抛出异常继续执行
        subprocess.run(["net", "stop", SERVICE_NAME], check=False, shell=True)
        
        # 等待2秒确保端口释放
        time.sleep(2)
        
        # 2. 启动服务
        # check=True 如果启动失败(配置错误等)，会抛出异常
        subprocess.run(["net", "start", SERVICE_NAME], check=True, shell=True)
        
        print(f"服务 {SERVICE_NAME} 重启成功，新配置已生效。")
        
    except subprocess.CalledProcessError as e:
        print(f"服务启动失败: {e}")
        print("请检查配置文件(config.json)是否有语法错误。")
    except Exception as e:
        print(f"重启服务时发生未知错误: {e}")

if __name__ == "__main__":
    # 启动时检查管理员权限
    if not is_admin():
        print("【警告】脚本未以管理员身份运行！")
        print("自动下载可以完成，但**无法自动重启服务**。")
        print("请右键点击脚本或终端，选择「以管理员身份运行」。")
        print("-" * 50)

    print(f"自动更新脚本已启动 (目标服务: {SERVICE_NAME})...")
    
    if not url:
        print("错误: 未在环境变量中找到 URL，请检查 .env 文件。")
        time.sleep(10)
        exit(1)

    while True:
        if should_update():
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                print(f"开始下载配置... (User-Agent: {headers['User-Agent']})")

                response = requests.get(url, headers=headers, timeout=(10, 30))
                response.raise_for_status()
                response.encoding = 'utf-8'

                try:
                    config_data = response.json()
                    
                    if "outbounds" in config_data:
                        # 写入文件
                        with open(save_path, "wb") as f:
                            f.write(response.content)

                        save_update_time()
                        print(f"配置文件下载成功 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # [核心修改] 下载成功后，执行重启服务
                        if is_admin():
                            restart_service()
                        else:
                            print("跳过服务重启（权限不足），请手动重启 Sing-box 服务。")
                    else:
                        print(f"校验失败：JSON 缺少 'outbounds' 字段 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                except json.JSONDecodeError:
                    print(f"校验失败：内容不是有效的 JSON - {time.strftime('%Y-%m-%d %H:%M:%S')}")

            except requests.exceptions.HTTPError as e:
                print(f"HTTP 错误: {e}")
            except requests.exceptions.ConnectionError:
                print("网络连接失败")
            except Exception as e:
                print(f"发生意外错误: {e}")
        # 每 10 秒检查一次，反应极其灵敏，且无性能压力
        time.sleep(10)