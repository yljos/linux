import os
import concurrent.futures
import threading

# Configuration
TARGET_MP4 = {"人间尤物"}
MIN_MP4_BYTES = 80 * 1024 * 1024
MAX_WORKERS = 5
ROOT_DIR = os.path.abspath(r"P:\My Pack")

print_lock = threading.Lock()

def delete_file(path: str) -> bool:
    try:
        os.remove(path)
        with print_lock: print(f"[Deleted] {path}")
        return True
    except Exception as e:
        with print_lock: print(f"[Error] {path}: {e}")
        return False

def main():
    script_path = os.path.abspath(__file__)
    files_to_del, folders = [], []

    # os.walk is optimized for WebDAV network I/O
    for root, dirs, files in os.walk(ROOT_DIR):
        # Prune protected directories in-place (Saves I/O)
        dirs[:] = [d for d in dirs if not d.startswith("#")]
        folders.append(root)

        for f in files:
            path = os.path.join(root, f)
            if f.startswith("#") or path == script_path:
                continue

            name, ext = os.path.splitext(f.lower())

            # Filtering logic
            if ext in (".mkv", ".avi"):
                continue
            if ext == ".mp4" and name not in TARGET_MP4:
                try:
                    if os.path.getsize(path) >= MIN_MP4_BYTES:
                        continue
                except OSError:
                    continue
            
            files_to_del.append(path)

    if not files_to_del:
        return print("No files to delete.")

    print(f"Deleting {len(files_to_del)} files...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(delete_file, files_to_del))

    # Cleanup empty folders bottom-up in a single pass
    deleted_folders = 0
    for d in reversed(folders):
        if d == ROOT_DIR: continue
        try:
            os.rmdir(d)
            deleted_folders += 1
        except OSError:
            pass

    print(f"Done! Files: {sum(results)}/{len(files_to_del)} | Empty Folders: {deleted_folders}")

if __name__ == "__main__":
    main()