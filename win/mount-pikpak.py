import os
import subprocess

# Configuration
conf_path = os.path.expandvars(r"%AppData%\rclone\rclone.conf")
pik_rc = "127.0.0.1:5573"
mount_point = "P:\\"

# Check if P: is mounted
if os.path.exists(mount_point):
    # Unmount if already mounted
    subprocess.run(["rclone", "rc", "core/quit", "--rc-addr", pik_rc])
else:
    # Mount if not mounted
    cmd = [
        "rclone", "mount", "pikpak:", "P:",
        "--config", conf_path,
        "--vfs-cache-mode", "full",
        "--vfs-cache-max-size", "10G",
        "--network-mode",
        "--no-console",
        "--rc",
        "--rc-no-auth",
        "--rc-addr", pik_rc,
        "--no-modtime",
        "--no-checksum"
    ]
    subprocess.Popen(cmd)