import time
import platform
import subprocess
import requests
from requests.exceptions import RequestException
import sys
import io

# 强制标准输出和错误输出使用 UTF-8 编码，防止中文乱码 (特别是在 Windows 环境下使用 -u 时)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置参数
HOST = "10.0.0.21"
PORT = 80
PATH = "/shutdown"
CHECK_INTERVAL_MINUTES = 5

def check_shutdown_signal(host, port, path):
    """检查URL内容是否为'1'"""
    try:
        url = f"http://{host}:{port}{path}"
        # 设置请求超时
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            content = response.text.strip()
            return content == "1"
    except RequestException as e:
        print(f"[!] 网络请求错误: {e}")
        
    return False

def shutdown_system():
    """执行系统关机"""
    system = platform.system()
    print(">>> 正在执行系统关机命令... <<<")

    try:
        if system == "Windows":
            # 强制关机，立即执行
            subprocess.run(["shutdown", "/s", "/f", "/t", "0"], check=True)
        elif system == "Linux" or system == "Darwin":
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        return True
    except subprocess.CalledProcessError as e:
         print(f"[!] 关机命令执行失败: {e}")
         return False

def main():
    """主循环"""
    print(f"开始监控 http://{HOST}:{PORT}{PATH}")
    print(f"检查间隔: {CHECK_INTERVAL_MINUTES} 分钟")

    wait_time_seconds = CHECK_INTERVAL_MINUTES * 60

    while True:
        try:
            # 检查远程信号
            if check_shutdown_signal(HOST, PORT, PATH):
                print("\n[!!!] 检测到关机信号 '1'，准备关机。")
                
                # 直接执行关机
                if shutdown_system():
                    break  # 关机成功，退出循环
                else:
                    print("[!] 关机失败，等待5秒后重试...")
                    time.sleep(5)
            else:
                 # 尚未收到关机信号
                print(f"[i] 未检测到关机信号。等待 {CHECK_INTERVAL_MINUTES} 分钟后再次检查...")
                time.sleep(wait_time_seconds)

        except KeyboardInterrupt:
            print("\n程序已被用户手动停止。")
            break
        except Exception as e:
            print(f"[!] 发生未知错误: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()