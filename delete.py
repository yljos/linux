import os
import concurrent.futures
import threading

# --- 配置 ---
# 1. 要保留的视频格式
VIDEO_EXTS = (".mp4", ".mkv", ".avi")

# 2. 要按文件名删除的 .mp4 文件黑名单（不含 .mp4 后缀，小写，精确匹配）
TARGET_MP4_NAMES = ["人间尤物"]

# 3. .mp4 文件大小阈值（单位: MB）
#    小于此大小的 .mp4 会被删除
MP4_SIZE_THRESHOLD_MB = 80

# 4. 并发线程数
MAX_WORKERS = 20

# --- 脚本开始 ---

# 全局线程锁，用于同步打印操作
print_lock = threading.Lock()


def delete_file(file_path):
    """删除单个文件。"""
    try:
        os.remove(file_path)
        return True, file_path
    except OSError as e:
        with print_lock:
            print(f"[错误] 删除失败 {file_path}: {e}")
        return False, file_path


def delete_empty_folders(directory):
    """删除所有空文件夹（多轮删除直到无可删除）。"""
    deleted_count = 0
    root_abs = os.path.abspath(directory)

    while True:
        removed = 0
        for root, dirs, files in os.walk(directory, topdown=False):
            if os.path.abspath(root) == root_abs:
                continue
            try:
                os.rmdir(root)
                deleted_count += 1
                removed += 1
            except OSError:
                continue
        if removed == 0:
            break

    return deleted_count


def should_delete_file(file_path, target_mp4_set, size_threshold_bytes):
    """判断单个文件是否应该被删除。

    保留规则：
    - .mp4 >= 80MB（且不在黑名单）
    - 所有 .mkv 和 .avi

    删除规则：
    - .mp4 < 80MB
    - 黑名单中的 .mp4
    - 所有其他文件
    """
    filename = os.path.basename(file_path)
    file_lower = filename.lower()

    # 视频格式处理
    if file_lower.endswith(VIDEO_EXTS):
        # .mkv 和 .avi 全部保留
        if not file_lower.endswith(".mp4"):
            return False

        # .mp4 黑名单直接删除
        name_part = os.path.splitext(filename)[0].lower()
        if name_part in target_mp4_set:
            return True

        # .mp4 按大小判断
        if size_threshold_bytes > 0:
            try:
                return os.path.getsize(file_path) < size_threshold_bytes
            except OSError:
                return False
        return False

    # 非视频格式：全部删除
    return True


def main():
    current_directory = os.getcwd()
    target_mp4_set = {name.lower() for name in TARGET_MP4_NAMES}
    size_threshold_bytes = MP4_SIZE_THRESHOLD_MB * 1024 * 1024
    script_path = os.path.abspath(__file__)

    print(f"目录: {current_directory}")
    print(f"保留: .mp4(≥{MP4_SIZE_THRESHOLD_MB}MB) .mkv .avi")
    if target_mp4_set:
        print(f"黑名单: {', '.join(TARGET_MP4_NAMES)}.mp4")
    print(f"删除: 所有其他文件")
    print("-" * 50)

    # 收集要删除的文件
    files_to_delete = []
    for root, dirs, files in os.walk(current_directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            if os.path.abspath(file_path) != script_path and should_delete_file(
                file_path, target_mp4_set, size_threshold_bytes
            ):
                files_to_delete.append(file_path)

    if not files_to_delete:
        print("未找到需要删除的文件。")
        return

    print(f"找到 {len(files_to_delete)} 个文件，开始删除...\n")

    # 并发删除
    deleted = failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for success, _ in executor.map(lambda f: delete_file(f), files_to_delete):
            if success:
                deleted += 1
            else:
                failed += 1

    # 清理空文件夹
    print(f"\n{'-' * 50}")
    print("清理空文件夹...")
    deleted_folders = delete_empty_folders(current_directory)

    # 总结
    print(f"\n{'=' * 50}")
    print(
        f"完成！删除文件: {deleted} 个 | 失败: {failed} 个 | 空文件夹: {deleted_folders} 个"
    )
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
