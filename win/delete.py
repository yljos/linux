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
TREE_OUTPUT_FILE = "mp4_tree.json"
DELETE_LIST_FILE = "delete_list.txt"

# 20MB threshold in bytes
MIN_MP4_SIZE_BYTES = 20 * 1024 * 1024

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
    mp4_tree = []

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
            mp4_tree.append(base_name)
            
            # Apply blacklist and size logic
            if any(b in base_name for b in BLACKLIST_MP4):
                files_to_del.append(rel_path)
            elif file_size < MIN_MP4_SIZE_BYTES:
                files_to_del.append(rel_path)
        else:
            files_to_del.append(rel_path)

    # Save MP4 tree (names only)
    mp4_tree.sort()
    with open(TREE_OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        json.dump(mp4_tree, f_out, ensure_ascii=False, indent=4)

    # Execute deletions
    if files_to_del:
        with open(DELETE_LIST_FILE, "w", encoding="utf-8") as f:
            for p in files_to_del:
                f.write(f"{p}\n")

        # Delete natively via rclone remote
        subprocess.run(["rclone", "delete", REMOTE_PATH, "--files-from", DELETE_LIST_FILE])

    # Native remote empty directory cleanup
    subprocess.run(["rclone", "rmdirs", REMOTE_PATH, "--leave-root"])

    # Remove temporary delete list
    # if os.path.exists(DELETE_LIST_FILE):
    #     os.remove(DELETE_LIST_FILE)

if __name__ == "__main__":
    main()