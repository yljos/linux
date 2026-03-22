import subprocess
import sys
from pathlib import Path

# ================= Configuration =================
# Use absolute paths for stability
RCLONE_EXE = Path(r"C:\rclone-v1.71.0-windows-amd64\rclone.exe")
CONFIG_PATH = Path(r"C:\Users\huai\AppData\Roaming\rclone\rclone.conf")

CMD = [
    str(RCLONE_EXE),
    "mount",
    "nas:/data",
    "Z:",
    "--config",
    str(CONFIG_PATH),
    "--vfs-cache-mode",
    "full",
    "--vfs-cache-max-size",
    "10G",
    "--network-mode",
    "--no-modtime",
    "--no-checksum",
    "--attr-timeout",
    "10s",
    "--dir-cache-time",
    "24h",
    "--vfs-fast-fingerprint",
    "--vfs-read-chunk-size",
    "128M",
    "--vfs-read-chunk-size-limit",
    "off",
    "--buffer-size",
    "32M",
    "--vfs-cache-max-age",
    "24h",
    "--sftp-ciphers",
    "aes128-gcm@openssh.com",
    "--vfs-links",  # Added to handle symlinks errors
    "--no-console",
]
# =================================================

if __name__ == "__main__":
    # Check config existence to prevent loop restarts
    if not CONFIG_PATH.exists():
        print(f"Error: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        # Execute rclone mount
        p = subprocess.Popen(CMD)
        p.wait()
        sys.exit(p.returncode)

    except KeyboardInterrupt:
        print(
            "Python: Termination signal received, waiting for Rclone to exit...",
            flush=True,
        )
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.terminate()
            sys.exit(1)
