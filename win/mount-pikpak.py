import os
import subprocess

# Configuration
conf_path = os.path.expandvars(r"%AppData%\rclone\rclone.conf")
pik_rc = "127.0.0.1:5573"
mount_point = "P:\\"
# Define cache directory on D drive to bypass UWF overlay on C:
cache_dir = "D:\\rclone_cache"

# Check if P: is mounted
if os.path.exists(mount_point):
    # Unmount if already mounted
    subprocess.run(["rclone", "rc", "core/quit", "--rc-addr", pik_rc])
else:
    # Mount if not mounted, explicitly setting the cache directory
    cmd = [
        "rclone",
        "mount",
        "pikpak:",
        "P:",
        "--config",
        conf_path,
        "--vfs-cache-mode",
        "full",
        "--cache-dir",
        cache_dir,
        "--vfs-cache-max-size",
        "10G",
        "--network-mode",
        "--no-console",
        "--rc",
        "--rc-no-auth",
        "--rc-addr",
        pik_rc,
        "--no-modtime",
        "--no-checksum",
        "--dir-cache-time", "72h",      
        "--attr-timeout", "72h",        
        "--vfs-read-chunk-size", "32M", 
    ]
    subprocess.Popen(cmd)