import subprocess
from pathlib import Path

# ================= Configuration =================
RCLONE_EXE = Path(r"C:\rclone-v1.71.0-windows-amd64\rclone.exe")
CONFIG_PATH = Path(r"C:\Users\huai\AppData\Roaming\rclone\rclone.conf")

CMD = [
    str(RCLONE_EXE), "mount", "nas:/data", "Z:",
    "--config", str(CONFIG_PATH),
    "--vfs-cache-mode", "full",
    "--network-mode",
    "--no-console",
    "--rc", "--rc-no-auth", "--rc-addr", "127.0.0.1:5572",
    "--sftp-ciphers", "aes128-gcm@openssh.com", # Hardware accelerated cipher
]

if __name__ == "__main__":
    # Launch rclone and exit the python script immediately
    subprocess.Popen(CMD)