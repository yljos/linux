import subprocess
from pathlib import Path

# ================= Configuration =================
RCLONE_EXE = Path(r"C:\rclone-v1.71.0-windows-amd64\rclone.exe")
CONFIG_PATH = Path(r"C:\Users\huai\AppData\Roaming\rclone\rclone.conf")

CMD = [
    str(RCLONE_EXE), "mount", "pikpak:", "P:",
    "--config", str(CONFIG_PATH),
    "--vfs-cache-mode", "full",
    "--vfs-cache-max-size", "10G",
    "--network-mode",
    "--no-console",
    "--rc", "--rc-no-auth", "--rc-addr", "127.0.0.1:5573",
    "--no-modtime", "--no-checksum", # Speed up for WebDAV
]

if __name__ == "__main__":
    subprocess.Popen(CMD)