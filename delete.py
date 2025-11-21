from pathlib import Path
import concurrent.futures
import threading

# --- 配置 ---
VIDEO_EXTS = (".mp4", ".mkv", ".avi")
TARGET_MP4_NAMES = ["人间尤物"]  # 不含 .mp4 后缀，小写
MP4_SIZE_THRESHOLD_MB = 80
MAX_WORKERS = 20

# --- 全局线程锁 ---
print_lock = threading.Lock()


def delete_file(path_obj: Path):
    try:
        path_obj.unlink(missing_ok=False)
        with print_lock:
            print(f"[Deleted] {path_obj}")
        return True
    except Exception as e:
        with print_lock:
            print(f"[Error] 删除失败 {path_obj}: {e}")
        return False


def delete_empty_folders(directory: Path):
    deleted = 0
    root = directory.absolute()

    while True:
        removed = 0
        for folder in sorted(
            directory.rglob("*"), key=lambda p: len(str(p)), reverse=True
        ):
            if folder.is_dir() and folder.absolute() != root:
                try:
                    folder.rmdir()
                    deleted += 1
                    removed += 1
                except OSError:
                    pass
        if removed == 0:
            break
    return deleted


def should_delete_file(path_obj: Path, target_mp4_set, size_threshold_bytes):
    filename = path_obj.name.lower()
    if filename.endswith(VIDEO_EXTS):
        if filename.endswith((".mkv", ".avi")):
            return False
        if path_obj.stem.lower() in target_mp4_set:
            return True
        try:
            return path_obj.stat().st_size < size_threshold_bytes
        except Exception:
            return False
    return True


def main():
    current_directory = Path(r"D:\My Pack").absolute()  # 目标目录
    script_path = Path(__file__).absolute()

    target_mp4_set = {name.lower() for name in TARGET_MP4_NAMES}
    size_threshold_bytes = MP4_SIZE_THRESHOLD_MB * 1024 * 1024

    print(f"目录: {current_directory}")
    print(f"保留: .mp4 ≥ {MP4_SIZE_THRESHOLD_MB}MB | .mkv | .avi")
    if target_mp4_set:
        print(f"黑名单: {', '.join(TARGET_MP4_NAMES)}.mp4")
    print("-" * 40)

    files_to_delete = [
        f
        for f in current_directory.rglob("*")
        if f.is_file()
        and f.absolute()
        != script_path.absolute()  # ✅ 用 absolute() 避免 WinError 1005
        and should_delete_file(f, target_mp4_set, size_threshold_bytes)
    ]

    if not files_to_delete:
        print("未找到需要删除的文件。")
        return

    print(f"找到 {len(files_to_delete)} 个文件，开始删除...\n")

    deleted = failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for success in executor.map(delete_file, files_to_delete):
            if success:
                deleted += 1
            else:
                failed += 1

    print("\n清理空文件夹...")
    deleted_folders = delete_empty_folders(current_directory)

    print("\n" + "=" * 50)
    print(f"完成！删除文件: {deleted} | 失败: {failed} | 空文件夹: {deleted_folders}")
    print("=" * 50)


if __name__ == "__main__":
    main()
