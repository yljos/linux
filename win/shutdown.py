import time
import platform
import subprocess
import requests
from requests.exceptions import RequestException
from pathlib import Path
import sys

# 配置参数
HOST = "10.0.0.21"
PORT = 80
PATH = "/shutdown"
CHECK_INTERVAL_MINUTES = 5

# 1. 工作指示文件路径配置
WORKING_FILE_PATH = Path(r"C:\shutdown\working")

# --- 状态变量：用于记忆是否曾经收到过关机信号 ---
# 初始化为 False，一旦检测到信号 '1'，即变为 True。
shutdown_requested = False


def check_shutdown_signal(host, port, path):
    """检查URL内容是否为'1'"""
    try:
        url = f"http://{host}:{port}{path}"
        # 将请求超时设置得短一些，避免阻塞
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            content = response.text.strip()
            return content == "1"
    except RequestException:
        pass

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
    except subprocess.CalledProcessError:
        return False


def main():
    """主循环"""
    global shutdown_requested

    print(f"开始监控 http://{HOST}:{PORT}{PATH}")
    print(f"检查间隔: {CHECK_INTERVAL_MINUTES} 分钟")
    print(f"工作指示文件路径: {WORKING_FILE_PATH}")

    wait_time_seconds = CHECK_INTERVAL_MINUTES * 60

    while True:
        try:
            # --- 步骤 1: 检查远程信号并更新记忆 ---
            # 无论 shutdown_requested 当前值是什么，都要检查。
            if check_shutdown_signal(HOST, PORT, PATH):
                if not shutdown_requested:
                    print("\n[!!!] 首次检测到关机信号 '1'。已进入待命关机模式。")
                shutdown_requested = True

            # --- 步骤 2: 根据记忆执行关机逻辑 ---
            if shutdown_requested:
                print(f"[*] 待命关机模式激活。检查工作文件状态...")

                # 检查工作文件是否存在
                if WORKING_FILE_PATH.exists():

                    # ** 只要文件存在，就无限等待 **
                    print(
                        f"   [等待中]: 发现工作文件 '{WORKING_FILE_PATH.name}' 存在。等待转换完成..."
                    )
                    time.sleep(wait_time_seconds)
                    continue
                else:
                    # 3. 工作文件不存在，执行关机
                    print(
                        "\n[✔] 条件满足：关机信号已接收，且工作指示文件已删除。执行关机。"
                    )
                    if shutdown_system():
                        break  # 关机成功，退出循环
                    else:
                        print("关机失败，等待5秒后继续...")
                        time.sleep(5)
            else:
                # 尚未收到关机信号
                print("[i] 关机信号未检测到。正常等待...")
                time.sleep(wait_time_seconds)

        except KeyboardInterrupt:
            print("\n程序已停止")
            break
        except Exception as e:
            print(f"发生未知错误: {e}")
            time.sleep(60)


if __name__ == "__main__":

    main()
