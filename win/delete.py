import os
import concurrent.futures
import threading
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
env_blacklist = os.getenv("BLACKLIST_MP4", "")
BLACKLIST_MP4 = {name.strip() for name in env_blacklist.split(",") if name.strip()}
WHITELIST_EXT = {".mkv", ".avi", ".mov", ".wmv"}

MAX_WORKERS = 10  # Tuned for WebDAV
ROOT_DIR = os.path.abspath(r"P:\My Pack")
TREE_OUTPUT_FILE = "mp4_tree.json"
DELETED_OUTPUT_FILE = "deleted_files.json"

print_lock = threading.Lock()


def delete_file(path: str) -> str:
    # [Phase 3: Network I/O]
    try:
        os.remove(path)
        with print_lock:
            print(f"[Deleted] {path}")
        return path
    except Exception as e:
        with print_lock:
            print(f"[Error] {path}: {e}")
        return ""


def main():
    script_path = os.path.abspath(__file__)
    
    # --- PHASE 1: Network I/O (Directory Traversal ONLY) ---
    print("Scanning network directory...")
    raw_files = []
    folders = []
    
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith("#")]
        folders.append(root)
        for f in files:
            if not f.startswith("#"):
                raw_files.append((root, f))

    # --- PHASE 2: Local Processing ---
    print("Processing data locally...")
    files_to_del = []
    mp4_tree = []

    for root, f in raw_files:
        path = os.path.join(root, f)
        if path == script_path:
            continue

        name, ext = os.path.splitext(f)
        ext_lower = ext.lower()

        if ext_lower in WHITELIST_EXT:
            continue

        if ext_lower == ".mp4":
            mp4_tree.append({"name": name, "path": path})
        else:
            files_to_del.append(path)

    # Write the full tree first
    mp4_tree.sort(key=lambda x: x["path"])
    with open(TREE_OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        json.dump(mp4_tree, f_out, ensure_ascii=False, indent=4)
    print(f"Generated local MP4 tree: {TREE_OUTPUT_FILE} ({len(mp4_tree)} MP4 files)")

    # Read and apply original blacklist logic
    with open(TREE_OUTPUT_FILE, "r", encoding="utf-8") as f_in:
        local_mp4_tree = json.load(f_in)

    for item in local_mp4_tree:
        if any(b in item["name"] for b in BLACKLIST_MP4):
            files_to_del.append(item["path"])

    # --- PHASE 3: Network I/O (Deletion Execution) ---
    successfully_deleted = []
    if files_to_del:
        print(f"Executing deletions over network ({len(files_to_del)} files)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            successfully_deleted = [p for p in pool.map(delete_file, files_to_del) if p]

        with open(DELETED_OUTPUT_FILE, "w", encoding="utf-8") as f_del:
            json.dump(successfully_deleted, f_del, ensure_ascii=False, indent=4)
        print(f"Generated deleted files log: {DELETED_OUTPUT_FILE}")
    else:
        print("No files to delete.")

    # Cleanup empty folders
    deleted_folders = 0
    for d in reversed(folders):
        if d == ROOT_DIR:
            continue
        try:
            os.rmdir(d)
            deleted_folders += 1
        except OSError:
            pass

    print(f"Done! Files Deleted: {len(successfully_deleted)}/{len(files_to_del)} | Empty Folders: {deleted_folders}")


if __name__ == "__main__":
    main()