import os
import json
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
env_blacklist = os.getenv("BLACKLIST_MP4", "")
BLACKLIST_MP4 = {name.strip() for name in env_blacklist.split(",") if name.strip()}
WHITELIST_EXT = {".mkv", ".avi", ".mov", ".wmv", ".ts"}

REMOTE_PATH = "pikpak:My Pack"

# 20MB threshold in bytes
MIN_MP4_SIZE_BYTES = 50 * 1024 * 1024

def main():
    # Fetch remote file tree
    cmd = ["rclone", "lsjson", REMOTE_PATH, "--recursive", "--files-only"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    if result.returncode != 0:
        return

    try:
        remote_files = json.loads(result.stdout)
    except json.JSONDecodeError:
        return

    files_to_del = []

    # Process JSON output
    for item in remote_files:
        rel_path = item["Path"]
        name = item["Name"]
        file_size = item.get("Size", 0)
        
        base_name, ext = os.path.splitext(name)
        ext_lower = ext.lower()

        if ext_lower in WHITELIST_EXT:
            continue

        if ext_lower == ".mp4":
            # Apply blacklist and size logic
            if any(b in base_name for b in BLACKLIST_MP4) or file_size < MIN_MP4_SIZE_BYTES:
                files_to_del.append(rel_path)
        else:
            files_to_del.append(rel_path)

    # Execute deletions via stdin (no temporary file)
    if files_to_del:
        delete_payload = "\n".join(files_to_del)
        subprocess.run(
            ["rclone", "delete", REMOTE_PATH, "--files-from", "-"],
            input=delete_payload,
            text=True,
            encoding="utf-8"
        )

    # Native remote empty directory cleanup
    subprocess.run(["rclone", "rmdirs", REMOTE_PATH, "--leave-root"])

if __name__ == "__main__":
    main()