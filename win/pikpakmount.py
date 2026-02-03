import subprocess
import sys
from pathlib import Path

# ================= 配置 =================
RCLONE_EXE = Path(r"C:\rclone-v1.71.0-windows-amd64\rclone.exe")

# ⚠️ 必须指定绝对路径，因为服务启动时无法正确获取当前用户的 home 目录
# 请将 '你的用户名' 替换为你实际的 Windows 用户名
CONFIG_PATH = Path(r"C:\Users\huai\AppData\Roaming\rclone\rclone.conf") 

CMD = [
    str(RCLONE_EXE),
    "mount",
    "pikpak:",
    "D:",
    "--config",           # 新增：指定配置文件参数
    str(CONFIG_PATH),     # 新增：配置文件路径
    "--vfs-cache-mode",
    "full",
    "--vfs-links",
    "--vfs-cache-max-size",
    "10G",
    "--no-console",
    # "--log-level", "INFO",
]
# =======================================

if __name__ == "__main__":
    # 简单的文件存在性检查，防止服务反复重启
    if not CONFIG_PATH.exists():
        print(f"Error: 配置文件未找到: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        p = subprocess.Popen(CMD)
        p.wait()
        sys.exit(p.returncode)

    except KeyboardInterrupt:
        print("Python: 接收到停止信号，正在等待 Rclone 退出...", flush=True)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.terminate()
            sys.exit(1)