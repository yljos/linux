import requests
import os
import time
import json
import subprocess
import ctypes
from dotenv import load_dotenv

# 核心映射配置字典 (Windows 10 环境)
APP_CONFIGS = {
    "clash": {
        "service_name": "Clash",
        "save_path": r"c:\free\config.yaml",
        "time_log_path": r"c:\free\clash_time",
        "default_ua": "clash_pc",
        "interval_hours": 1
    },
    "sing-box": {
        "service_name": "Sing-Box",
        "save_path": r"c:\free\config.json",
        "time_log_path": r"c:\free\sing-box_time",
        "default_ua": "sing-box_pc",
        "interval_hours": 1
    }
}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_last_update_time(time_log_path):
    try:
        if os.path.exists(time_log_path):
            with open(time_log_path, "r") as f:
                content = f.read().strip()
                if content:
                    return float(content)
    except Exception:
        pass
    return 0

def save_update_time(time_log_path):
    try:
        os.makedirs(os.path.dirname(time_log_path), exist_ok=True)
        with open(time_log_path, "w") as f:
            f.write(str(time.time()))
    except Exception as e:
        print(f"保存时间戳失败: {e}")

def should_update(time_log_path, interval_hours):
    last_time = get_last_update_time(time_log_path)
    current_time = time.time()
    hours_passed = (current_time - last_time) / 3600
    
    if last_time == 0:
        return True
    return hours_passed >= interval_hours

def validate_content(app, text):
    """根据目标应用执行专属的内容格式校验"""
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    
    if app == "clash":
        if "proxies:" in text:
            return True
        print(f"校验失败：下载内容不包含 'proxies:' - {time_str}")
        return False
        
    elif app == "sing-box":
        try:
            data = json.loads(text)
            if "outbounds" in data:
                return True
            print(f"校验失败：JSON 缺少 'outbounds' 字段 - {time_str}")
            return False
        except json.JSONDecodeError:
            print(f"校验失败：内容不是有效的 JSON - {time_str}")
            return False
            
    return False

def restart_service(service_name):
    print(f"正在尝试重启服务: {service_name} ...")
    try:
        subprocess.run(["net", "stop", service_name], check=False, shell=True)
        time.sleep(2)
        subprocess.run(["net", "start", service_name], check=True, shell=True)
        print(f"[成功] 服务 {service_name} 重启成功，新配置已生效。")
    except subprocess.CalledProcessError as e:
        print(f"[失败] 服务启动失败: {e}")
        print("请检查配置文件是否有语法错误。")
    except Exception as e:
        print(f"重启服务时发生未知错误: {e}")


if __name__ == "__main__":
    if not is_admin():
        print("【警告】脚本未以管理员身份运行！")
        print("自动下载可以完成，但**无法自动重启服务**。")
        print("请右键点击脚本或终端，选择「以管理员身份运行」。")
        print("-" * 50)

    print("自动更新守护进程已启动，等待读取环境配置...")

    try:
        while True:
            # 动态加载环境变量
            load_dotenv(override=True)
            target_app = os.getenv("TARGET_APP", "").strip().lower()

            if target_app not in APP_CONFIGS:
                print(f"[{time.strftime('%H:%M:%S')}] 错误: TARGET_APP 变量未设置或不合法。请在 .env 中设置为 'clash' 或 'sing-box'。")
                time.sleep(10)
                continue

            cfg = APP_CONFIGS[target_app]
            
            if should_update(cfg["time_log_path"], cfg["interval_hours"]):
                url = os.getenv("URL")
                user_agent = os.getenv("USER_AGENT", cfg["default_ua"])
                headers = {"User-Agent": user_agent}

                if not url:
                    print("错误: 未在 .env 文件中找到 URL，请检查配置。")
                    time.sleep(10)
                    continue

                try:
                    os.makedirs(os.path.dirname(cfg["save_path"]), exist_ok=True)
                    print(f"开始下载 {cfg['service_name']} 配置... (User-Agent: {user_agent})")

                    response = requests.get(url, headers=headers, timeout=(10, 30))
                    response.raise_for_status()
                    response.encoding = 'utf-8'

                    # 调用对应的校验逻辑
                    if validate_content(target_app, response.text):
                        with open(cfg["save_path"], "wb") as f:
                            f.write(response.content)

                        save_update_time(cfg["time_log_path"])
                        print(f"[{cfg['service_name']}] 配置文件更新成功 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

                        if is_admin():
                            restart_service(cfg["service_name"])
                        else:
                            print(f"跳过服务重启（权限不足），请手动重启 {cfg['service_name']} 服务。")
                    
                except requests.exceptions.HTTPError as e:
                    print(f"HTTP 错误: {e}")
                except requests.exceptions.ConnectionError:
                    print("网络连接失败，请检查网络或 URL 是否正确")
                except requests.exceptions.Timeout:
                    print("请求超时，正在等待下次重试")
                except Exception as e:
                    print(f"发生意外错误: {e}")

            # 每 10 秒检查一次是否触发更新或者是否修改了 TARGET_APP
            time.sleep(10)

    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 服务已手动停止。")
    except Exception as e:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 发生致命错误导致停止: {e}")