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
    # Unmount via remote control
    subprocess.run(["rclone", "rc", "core/quit", "--rc-addr", pik_rc])
else:
    # Mount with optimized parameters for PikPak API and streaming
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
        "--volname",
        "PikPak",  # Clean volume name
        "--no-console",
        "--rc",
        "--rc-no-auth",
        "--rc-addr",
        pik_rc,
        "--no-modtime",  # Avoid extra API calls for modification times
        "--no-checksum",  # Avoid hashing overhead
        "--dir-cache-time",
        "12h",  # Balanced sync time for native API
        "--attr-timeout",
        "12h",
        "--vfs-read-chunk-size",
        "32M",
        "--vfs-read-chunk-size-limit",
        "2G",  # Ramp up chunk size to prevent API rate limiting during video playback
    ]
    subprocess.Popen(cmd)
