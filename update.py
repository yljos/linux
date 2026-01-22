import requests
import os
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

url = os.getenv("URL")
# [修改] 从环境变量读取 User-Agent，如果没有配置则默认使用 "clash_pc"
user_agent = os.getenv("USER_AGENT", "clash_pc")

save_path = r"c:\mihomo\config.yaml"
time_log_path = r"c:\mihomo\updatetime"

# [修改] 使用变量定义 headers
headers = {"User-Agent": user_agent}


def get_last_update_time():
    """读取上次更新时间"""
    try:
        if os.path.exists(time_log_path):
            with open(time_log_path, "r") as f:
                timestamp = float(f.read().strip())
                return timestamp
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
    return hours_passed >= 12


if __name__ == "__main__":
    print("自动更新脚本已启动 (使用 requests 库)...")

    # 预检查：确保 URL 存在
    if not url:
        print("错误: 环境变量中未找到 URL，请检查 .env 文件")
        exit(1)

    while True:
        if should_update():
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                print(f"开始下载配置... (User-Agent: {headers['User-Agent']})")

                # 使用 requests 发起请求
                # timeout=(连接超时, 读取超时)
                response = requests.get(url, headers=headers, timeout=(10, 30))

                # 检查状态码，如果不是 200 会抛出 HTTPError 异常
                response.raise_for_status()

                # [新增] 校验：检查下载内容是否包含 'proxies:'
                if "proxies:" in response.text:
                    # 写入文件 (使用 response.content 获取二进制内容)
                    with open(save_path, "wb") as f:
                        f.write(response.content)

                    save_update_time()
                    print(f"配置文件更新成功 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    # 如果校验失败
                    print(f"校验失败：下载内容不包含 'proxies:'，跳过写入 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

            except requests.exceptions.HTTPError as e:
                print(f"HTTP 错误: {e}")
            except requests.exceptions.ConnectionError:
                print("网络连接失败，请检查网络或 URL 是否正确")
            except requests.exceptions.Timeout:
                print("请求超时，正在等待下次重试")
            except Exception as e:
                print(f"发生意外错误: {e}")

        # 每10分钟检查一次 (600秒)
        time.sleep(600)