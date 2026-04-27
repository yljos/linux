import os
import concurrent.futures
import threading

# --- Config ---
VIDEO_EXTS = (".mp4", ".mkv", ".avi")
TARGET_MP4_NAMES = {"人间尤物"}  # Store as set for O(1) lookup, lowercase
MP4_SIZE_THRESHOLD_MB = 80
MP4_SIZE_THRESHOLD_BYTES = MP4_SIZE_THRESHOLD_MB * 1024 * 1024

# Reduced max workers to avoid triggering WebDAV rate limits (e.g., 429/503 errors)
MAX_WORKERS = 5 

# --- Global Thread Lock ---
print_lock = threading.Lock()

def delete_file(file_path: str) -> bool:
    try:
        os.remove(file_path)
        with print_lock:
            print(f"[Deleted] {file_path}")
        return True
    except Exception as e:
        with print_lock:
            print(f"[Error] Failed {file_path}: {e}")
        return False

def main():
    current_directory = os.path.abspath(r"P:\My Pack")
    script_path = os.path.abspath(__file__)

    print(f"Directory: {current_directory}")
    print(f"Keep: .mp4 (>= {MP4_SIZE_THRESHOLD_MB}MB) | .mkv | .avi | path contains #")
    print("-" * 40)

    files_to_delete = []
    folders_to_check = []

    # Use os.walk for WebDAV. It uses os.scandir internally,
    # which drastically reduces network requests compared to Path.rglob().
    for root, dirs, files in os.walk(current_directory):
        try:
            rel_path = os.path.relpath(root, current_directory)
        except ValueError:
            rel_path = ""

        # Check if current directory path is protected
        parts = rel_path.split(os.sep)
        if any(p.startswith("#") for p in parts if p != "."):
            # Clear dirs to prevent os.walk from descending further into this protected branch (Saves I/O)
            dirs.clear()
            continue

        # Store folders for a single-pass bottom-up cleanup later
        folders_to_check.append(root)

        for file in files:
            file_path = os.path.join(root, file)
            if file_path == script_path:
                continue

            if file.startswith("#"):
                continue

            lower_file = file.lower()
            should_delete = True

            if lower_file.endswith(VIDEO_EXTS):
                if lower_file.endswith((".mkv", ".avi")):
                    should_delete = False
                elif os.path.splitext(lower_file)[0] in TARGET_MP4_NAMES:
                    should_delete = True
                else:
                    # Lazy stat: Only fetch file size via network if absolutely necessary
                    try:
                        if os.path.getsize(file_path) >= MP4_SIZE_THRESHOLD_BYTES:
                            should_delete = False
                    except OSError:
                        should_delete = False

            if should_delete:
                files_to_delete.append(file_path)

    if not files_to_delete:
        print("No files to delete.")
        return

    print(f"Found {len(files_to_delete)} files, deleting...\n")

    deleted = failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for success in executor.map(delete_file, files_to_delete):
            if success:
                deleted += 1
            else:
                failed += 1

    print("\nCleaning empty folders...")
    deleted_folders = 0
    
    # Iterate from deepest to shallowest to clean up in a single pass without extra network scanning
    for folder in reversed(folders_to_check):
        if folder == current_directory:
            continue
        try:
            # os.rmdir succeeds only if the directory is empty
            os.rmdir(folder)
            deleted_folders += 1
        except OSError:
            pass

    print("\n" + "=" * 50)
    print(f"Done! Deleted files: {deleted} | Failed: {failed} | Empty folders: {deleted_folders}")
    print("=" * 50)

if __name__ == "__main__":
    main()