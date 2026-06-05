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
        # --- 极简优化：目录与属性缓存 ---
        "--dir-cache-time", "72h",      # 将目录结构缓存在本地内存长达 72 小时
        "--attr-timeout", "72h",        # 缓存文件属性（极大幅度减少 os.walk 的延迟）
        "--vfs-read-chunk-size", "32M", # 针对 MP4 视频优化的读取块大小，提升加载速度
    ]
    subprocess.Popen(cmd)