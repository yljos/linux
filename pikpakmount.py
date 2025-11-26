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
]
# =======================================

if __name__ == "__main__":
    try:
        # 启动 Rclone
        p = subprocess.Popen(CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 阻塞等待
        p.wait()
        sys.exit(p.returncode)

    except KeyboardInterrupt:
        # 【关键修改】
        # 当 NSSM 发送停止信号时，Python 和 Rclone 都会收到 Ctrl+C。
        # Rclone 收到信号后，会开始清理缓存、断开连接。
        # 我们这里千万不要 p.terminate()，而是要等它自己结束。
        try:
            # 给他 5 秒钟时间优雅退出
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 如果 5 秒了还赖着不走，再强制杀掉
            p.terminate()
            sys.exit(1)
