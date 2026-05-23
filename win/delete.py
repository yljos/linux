import os
import concurrent.futures
import threading
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
env_blacklist = os.getenv("BLACKLIST_MP4", "")
# Keep exact case for blacklist terms
BLACKLIST_MP4 = {name.strip() for name in env_blacklist.split(",") if name.strip()}

MAX_WORKERS = 5
ROOT_DIR = os.path.abspath(r"P:\My Pack")
TREE_OUTPUT_FILE = "mp4_tree.json"

print_lock = threading.Lock()


def delete_file(path: str) -> bool:
    try:
        os.remove(path)
        with print_lock:
            print(f"[Deleted] {path}")
        return True
    except Exception as e:
        with print_lock:
            print(f"[Error] {path}: {e}")
        return False


def main():
    script_path = os.path.abspath(__file__)
    files_to_del, folders = [], []
    seen_mp4_names = set()

    # os.walk is optimized for WebDAV network I/O
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith("#")]
        folders.append(root)

        for f in files:
            path = os.path.join(root, f)
            if f.startswith("#") or path == script_path:
                continue

            name, ext = os.path.splitext(f)
            ext_lower = ext.lower()  # Only lowercase the extension

            if ext_lower == ".mp4":
                seen_mp4_names.add(name)  # Store original case name

            if ext_lower in (".mkv", ".avi", ".mov", ".wmv"):
                continue

            # Strict exact substring matching for mp4 blacklist (case-sensitive)
            if ext_lower == ".mp4" and not any(b in name for b in BLACKLIST_MP4):
                continue

            files_to_del.append(path)

    # Write the unique names to file as formatted JSON
    with open(TREE_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen_mp4_names)), f, ensure_ascii=False, indent=4)

    print(
        f"Generated local MP4 tree: {TREE_OUTPUT_FILE} ({len(seen_mp4_names)} unique names)"
    )

    if not files_to_del:
        return print("No files to delete.")

    print(f"Deleting {len(files_to_del)} files...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(delete_file, files_to_del))

    # Cleanup empty folders bottom-up in a single pass
    deleted_folders = 0
    for d in reversed(folders):
        if d == ROOT_DIR:
            continue
        try:
            os.rmdir(d)
            deleted_folders += 1
        except OSError:
            pass

    print(
        f"Done! Files: {sum(results)}/{len(files_to_del)} | Empty Folders: {deleted_folders}"
    )


if __name__ == "__main__":
    main()
