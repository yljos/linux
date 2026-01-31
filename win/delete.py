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


def is_protected(path_obj: Path, root: Path) -> bool:
    """
    检查路径是否受保护：
    如果路径中（相对于根目录）的任意一部分（文件夹或文件名）以 # 开头，则视为受保护。
    """
    try:
        # 获取相对于根目录的路径部分
        parts = path_obj.relative_to(root).parts
        # 只要有一部分以 # 开头，就返回 True
        return any(part.startswith("#") for part in parts)
    except ValueError:
        return False


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
        # 由深到浅遍历文件夹
        for folder in sorted(
            directory.rglob("*"), key=lambda p: len(str(p)), reverse=True
        ):
            if folder.is_dir() and folder.absolute() != root:
                # --- 修改点：检查文件夹是否受保护 ---
                if is_protected(folder, root):
                    continue

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
    """
    判断文件是否应该被删除
    """
    filename = path_obj.name.lower()

    # 1. 检查是否为视频文件
    if filename.endswith(VIDEO_EXTS):
        # 保留 .mkv 和 .avi
        if filename.endswith((".mkv", ".avi")):
            return False

        # 删除黑名单中的文件
        if path_obj.stem.lower() in target_mp4_set:
            return True

        # 注意：文件名以 # 开头的保护逻辑现已包含在 main 的 is_protected 检查中，
        # 但保留此处逻辑作为双重保险无妨。
        if path_obj.name.startswith("#"):
            return False

        # 检查大小：小于阈值则删除
        try:
            return path_obj.stat().st_size < size_threshold_bytes
        except Exception:
            return False

    # 2. 非视频文件，删除
    return True


def main():
    current_directory = Path(r"D:\My Pack").absolute()  # 目标目录
    script_path = Path(__file__).absolute()

    target_mp4_set = {name.lower() for name in TARGET_MP4_NAMES}
    size_threshold_bytes = MP4_SIZE_THRESHOLD_MB * 1024 * 1024

    print(f"目录: {current_directory}")
    print(f"保留: .mp4 (≥ {MP4_SIZE_THRESHOLD_MB}MB) | .mkv | .avi | 路径含 #")
    if target_mp4_set:
        print(f"黑名单: {', '.join(TARGET_MP4_NAMES)}.mp4")
    print("-" * 40)

    # 收集文件时，先排除掉受保护路径
    files_to_delete = [
        f
        for f in current_directory.rglob("*")
        if f.is_file()
        and f.absolute() != script_path.absolute()
        and not is_protected(
            f, current_directory
        )  # --- 修改点：排除路径带 # 的文件 ---
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
