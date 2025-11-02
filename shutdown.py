import time
import platform
import subprocess
import requests
from requests.exceptions import RequestException

# 配置参数
HOST = "192.168.31.21"
PORT = 80
PATH = "/shutdown"
CHECK_INTERVAL_MINUTES = 5


def check_shutdown_signal(host, port, path):
    """检查URL内容是否为'1'"""
    try:
        url = f"http://{host}:{port}{path}"
        response = requests.get(url, timeout=10)

        # 检查状态码是否为200
        if response.status_code == 200:
            # 去除空白字符后检查内容是否为"1"
            content = response.text.strip()
            return content == "1"
    except RequestException:
        # 网络错误时返回False
        pass

    return False


def shutdown_system():
    """执行系统关机"""
    system = platform.system()

    try:
        if system == "Windows":
            # Windows关机命令
            subprocess.run(["shutdown", "/s", "/f", "/t", "0"], check=True)
        elif system == "Linux" or system == "Darwin":  # Darwin是macOS
            # Linux/macOS关机命令
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """主循环"""
    print(f"开始监控 http://{HOST}:{PORT}{PATH}")
    print(f"检查间隔: {CHECK_INTERVAL_MINUTES} 分钟")

    while True:
        try:
            # 检查关机信号
            if check_shutdown_signal(HOST, PORT, PATH):
                print("检测到关机信号，准备关机...")
                if shutdown_system():
                    break  # 关机成功，退出循环
                else:
                    print("关机失败，等待5秒后继续...")
                    time.sleep(5)
            else:
                # 等待指定时间后再次检查
                time.sleep(CHECK_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n程序已停止")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            time.sleep(60)  # 发生错误时等待1分钟


if __name__ == "__main__":
    main()
