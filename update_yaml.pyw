import requests
import os
import time
import subprocess
import ctypes
import sys
from dotenv import load_dotenv

# 加载环境变量 (保持原样)
load_dotenv()

# 配置信息
url = os.getenv("URL")
user_agent = os.getenv("USER_AGENT", "clash_pc")
# 定义服务名称
SERVICE_NAME = "Mihomo"

save_path = r"c:\mihomo\config.yaml"
time_log_path = r"c:\mihomo\updatetime"

# 使用变量定义 headers
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
        
    return hours_passed >= 12

def restart_service():
    """重启 Mihomo 服务"""
    print(f"正在尝试重启服务: {SERVICE_NAME} ...")
    try:
        # 1. 停止服务
        subprocess.run(["net", "stop", SERVICE_NAME], check=False, shell=True)
        
        # 等待2秒确保端口释放
        time.sleep(2)
        
        # 2. 启动服务
        subprocess.run(["net", "start", SERVICE_NAME], check=True, shell=True)
        
        # [修改] 移除 Emoji 防止报错
        print(f"[成功] 服务 {SERVICE_NAME} 重启成功，新配置已生效。")
        
    except subprocess.CalledProcessError as e:
        # [修改] 移除 Emoji 防止报错
        print(f"[失败] 服务启动失败: {e}")
        print("请检查配置文件(config.yaml)是否有语法错误。")
    except Exception as e:
        print(f"重启服务时发生未知错误: {e}")

if __name__ == "__main__":
    # 启动时检查管理员权限
    if not is_admin():
        print("【警告】脚本未以管理员身份运行！")
        print("自动下载可以完成，但**无法自动重启服务**。")
        print("请确保在 nssm 中服务登录身份为 Local System (本地系统)，或以管理员运行脚本。")
        print("-" * 50)

    print(f"自动更新脚本已启动 (目标服务: {SERVICE_NAME})...")

    # 检查 URL 是否存在
    if not url:
        print("错误: 未在环境变量中找到 URL，请检查 .env 文件。")
        time.sleep(10)
        exit(1)

    # [新增] 捕获停止信号
    try:
        while True:
            if should_update():
                try:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    print(f"开始下载配置... (User-Agent: {headers['User-Agent']})")

                    response = requests.get(url, headers=headers, timeout=(10, 30))
                    response.raise_for_status()

                    # [保持原样] 你原来代码里加了 utf-8
                    response.encoding = 'utf-8'

                    if "proxies:" in response.text:
                        with open(save_path, "wb") as f:
                            f.write(response.content)

                        save_update_time()
                        print(f"配置文件更新成功 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if is_admin():
                            restart_service()
                        else:
                            print("跳过服务重启（权限不足），请手动重启 Mihomo 服务。")

                    else:
                        print(f"校验失败：下载内容不包含 'proxies:'，跳过写入 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

                except requests.exceptions.HTTPError as e:
                    print(f"HTTP 错误: {e}")
                except requests.exceptions.ConnectionError:
                    print("网络连接失败，请检查网络或 URL 是否正确")
                except requests.exceptions.Timeout:
                    print("请求超时，正在等待下次重试")
                except Exception as e:
                    print(f"发生意外错误: {e}")

            time.sleep(10)

    # [核心修改] 捕获手动停止信号
    except KeyboardInterrupt:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 服务已手动停止。")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 服务因未知错误停止: {e}")