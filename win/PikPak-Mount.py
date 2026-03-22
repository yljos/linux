import subprocess
import sys
from pathlib import Path

# ================= Configuration =================
RCLONE_EXE = Path(r"C:\rclone-v1.71.0-windows-amd64\rclone.exe")
CONFIG_PATH = Path(r"C:\Users\huai\AppData\Roaming\rclone\rclone.conf")

CMD = [
    str(RCLONE_EXE),
    "mount",
    "pikpak:",
    "P:",
    "--config",
    str(CONFIG_PATH),
    "--vfs-cache-mode",
    "full",
    "--vfs-cache-max-size",
    "10G",
    "--network-mode",  # 核心新增：开启网络模式
    "--vfs-links",  # 处理软链接
    "--no-console",
    "--no-modtime",  # 极简优化：减少元数据读写，提升响应速度
    "--no-checksum",  # 提升挂载启动速度
    "--attr-timeout",
    "10s",
]
# =================================================

if __name__ == "__main__":
    if not CONFIG_PATH.exists():
        print(f"Error: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        # 使用 subprocess 启动并等待
        p = subprocess.Popen(CMD)
        p.wait()
        sys.exit(p.returncode)

    except KeyboardInterrupt:
        print("Python: Interrupted, closing Rclone...", flush=True)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.terminate()
            sys.exit(1)
