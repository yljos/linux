import os
import time
import subprocess
import ctypes
from dotenv import load_dotenv
from curl_cffi import requests # Using open source curl_cffi to bypass Cloudflare

# Configuration
SERVICE_NAME = "Mihomo"
save_path = r"c:\mihomo\config.yaml"
time_log_path = r"c:\mihomo\updatetime"


def is_admin():
    """Check for administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def get_last_update_time():
    """Read the last update time"""
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
    """Save the current update time"""
    try:
        os.makedirs(os.path.dirname(time_log_path), exist_ok=True)
        with open(time_log_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"保存时间戳失败: {e}")


def should_update():
    """Determine if an update is needed"""
    last_time = get_last_update_time()
    current_time = time.time()
    hours_passed = (current_time - last_time) / 3600

    if last_time == 0:
        return True

    return hours_passed >= 1  # Check once per hour


def restart_service():
    """Restart the Mihomo service"""
    print(f"正在尝试重启服务: {SERVICE_NAME} ...")
    try:
        # 1. Stop service
        subprocess.run(["net", "stop", SERVICE_NAME], check=False, shell=True)

        # Wait 2 seconds to ensure port is released
        time.sleep(2)

        # 2. Start service
        subprocess.run(["net", "start", SERVICE_NAME], check=True, shell=True)

        print(f"[成功] 服务 {SERVICE_NAME} 重启成功，新配置已生效。")

    except subprocess.CalledProcessError as e:
        print(f"[失败] 服务启动失败: {e}")
        print("请检查配置文件(config.yaml)是否有语法错误。")
    except Exception as e:
        print(f"重启服务时发生未知错误: {e}")


if __name__ == "__main__":

    print(f"自动更新脚本已启动 (目标服务: {SERVICE_NAME})...")

    # Catch termination signals
    try:
        while True:
            if should_update():
                # Dynamically load env vars before each execution
                load_dotenv(override=True)
                url = os.getenv("URL")
                user_agent = os.getenv("USER_AGENT", "clash_pc")
                headers = {"User-Agent": user_agent}

                if not url:
                    print("错误: 未在 .env 文件中找到 URL，跳过本次更新。")
                    time.sleep(10)
                    continue

                try:
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    print(f"开始下载配置... (User-Agent: {headers['User-Agent']})")

                    # Bypass Bot Fight Mode by impersonating Chrome
                    response = requests.get(url, headers=headers, timeout=(10, 30), impersonate="chrome")
                    response.raise_for_status()
                    response.encoding = "utf-8"

                    if "proxies:" in response.text:
                        with open(save_path, "wb") as f:
                            f.write(response.content)

                        save_update_time()
                        print(
                            f"配置文件更新成功 - {time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )

                        if is_admin():
                            restart_service()

                    else:
                        print(
                            f"校验失败：下载内容不包含 'proxies:'，跳过写入 - {time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )

                except requests.exceptions.HTTPError as e:
                    print(f"HTTP 错误: {e}")
                except requests.exceptions.ConnectionError:
                    print("网络连接失败，请检查网络或 URL 是否正确")
                except requests.exceptions.Timeout:
                    print("请求超时，正在等待下次重试")
                except Exception as e:
                    print(f"发生意外错误: {e}")

            time.sleep(10)

    except KeyboardInterrupt:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 服务已手动停止。")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 服务因未知错误停止: {e}")