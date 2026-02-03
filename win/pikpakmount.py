import subprocess
import sys
from pathlib import Path

# ================= 配置 =================
RCLONE_EXE = Path(r"C:\rclone-v1.71.0-windows-amd64\rclone.exe")
CMD = [
    str(RCLONE_EXE),
    "mount",
    "pikpak:",
    "D:",
    "--vfs-cache-mode",
    "full",
    "--vfs-links",
    "--vfs-cache-max-size",
    "10G",
    "--no-console",
    # 注意：如果要在 NSSM 日志里看到 rclone 内部的详细输出，
    # 可以根据需要取消下面两行的注释，并调整 log-level
    # "--log-level", "INFO",
]
# =======================================

if __name__ == "__main__":
    try:
        # 去掉 stdout=DEVNULL，让 NSSM 能够捕获输出
        p = subprocess.Popen(CMD)
        p.wait()
        sys.exit(p.returncode)

    except KeyboardInterrupt:
        # 这里的 print 会被 NSSM 记录到 AppStdout
        print("Python: 接收到停止信号，正在等待 Rclone 退出...", flush=True)
        try:
            # 这里的 timeout 参数是 subprocess 自带的功能，不需要 import time
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.terminate()
            sys.exit(1)