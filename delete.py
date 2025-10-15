import os
import sys
import concurrent.futures
import threading

# --- 配置 ---
# 1. 要按扩展名删除的文件类型 (小写)
TARGET_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".apk",
    ".zip",
    ".mhtml",
    ".gif",
    ".chm",
    ".rar",
    ".txt",
    ".dat",
    ".bt",
    ".torrent",
    ".bc!",
    ".doc",
]

# 2. 要按文件名删除的 .mp4 文件列表 (不含.mp4后缀, 小写, 精确匹配)
#    如果要删除所有名为 '缓存' 和 '广告' 的mp4, 设置为: ['缓存', '广告']
TARGET_MP4_NAMES = ["人间尤物"]

# 3. 新功能：删除小于指定大小的 .mp4 文件 (单位: MB)
#    设置为 20 就会删除所有小于 20MB 的 .mp4 文件。
#    如果不想使用此功能，请将其设置为 0
MP4_SIZE_THRESHOLD_MB = 60

# 4. 新功能：是否删除没有扩展名的文件
#    设置为 True 会删除所有没有扩展名的文件（不包含 . 的文件名）
#    设置为 False 则不删除无扩展名文件
DELETE_NO_EXTENSION = True

# 5. 并发线程数
MAX_WORKERS = 20

# --- 脚本开始 ---

# 全局线程锁，用于同步打印操作
print_lock = threading.Lock()


def delete_file(file_path):
    """删除单个文件的函数。"""
    with print_lock:
        print(f"[文件] 正在删除: {file_path}")
    try:
        os.remove(file_path)
        return True, file_path
    except OSError as e:
        with print_lock:
            print(f"[错误] 删除文件失败 {file_path} : {e}")
        return False, file_path


def delete_empty_folders(directory):
    """删除指定目录下的所有空文件夹。"""
    deleted_folders_count = 0
    print("\n" + "-" * 30)
    print("开始检查并删除空文件夹...")
    # 从最内层目录开始向上遍历 (topdown=False)
    for root, dirs, files in os.walk(directory, topdown=False):
        if not dirs and not files:
            try:
                with print_lock:
                    print(f"[目录] 正在删除: {root}")
                os.rmdir(root)
                deleted_folders_count += 1
            except OSError as e:
                with print_lock:
                    print(f"[错误] 删除空文件夹失败 {root}: {e}")
    print(f"空文件夹清理完成。")
    return deleted_folders_count


def main():
    current_directory = os.getcwd()
    target_mp4_set = {name.lower() for name in TARGET_MP4_NAMES}
    # 将MB转换为字节
    size_threshold_bytes = MP4_SIZE_THRESHOLD_MB * 1024 * 1024

    print(f"将在 '{current_directory}' 中搜索并删除...")
    print(f"目标扩展名: {', '.join(TARGET_EXTENSIONS)}")
    if target_mp4_set:
        print(f"指定 .mp4 文件名: {', '.join(TARGET_MP4_NAMES)}")
    if size_threshold_bytes > 0:
        print(f"删除小于 {MP4_SIZE_THRESHOLD_MB}MB 的 .mp4 文件")
    if DELETE_NO_EXTENSION:
        print(f"删除没有扩展名的文件")
    print(f"并发数: {MAX_WORKERS}")
    print("-" * 30)

    deleted_count = 0
    failed_count = 0
    total_found = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []

        for root, dirs, files in os.walk(current_directory):
            for filename in files:
                file_lower = filename.lower()
                file_path = os.path.join(root, filename)
                should_delete = False

                # 条件1: 匹配扩展名列表
                if any(
                    filename.endswith(ext) or filename.endswith(ext.upper())
                    for ext in TARGET_EXTENSIONS
                ):
                    should_delete = True

                # 条件2: 删除没有扩展名的文件
                elif DELETE_NO_EXTENSION and "." not in filename:
                    should_delete = True

                # 条件3: 如果是.mp4文件，则应用特定规则
                elif file_lower.endswith(".mp4"):
                    # 子条件2a: 匹配指定文件名
                    name_part = os.path.splitext(filename)[0].lower()
                    if name_part in target_mp4_set:
                        should_delete = True
                    # 子条件2b: 匹配文件大小
                    elif size_threshold_bytes > 0:
                        try:
                            file_size = os.path.getsize(file_path)
                            if file_size < size_threshold_bytes:
                                should_delete = True
                        except OSError:
                            # 如果文件无法访问，则跳过
                            continue

                if should_delete:
                    total_found += 1
                    future = executor.submit(delete_file, file_path)
                    futures.append(future)

        if not futures:
            print("未找到任何符合条件的文件。")
        else:
            print(f"[*] 已找到 {len(futures)} 个文件，删除操作已开始...")

        for future in concurrent.futures.as_completed(futures):
            success, _ = future.result()
            if success:
                deleted_count += 1
            else:
                failed_count += 1

    # 清理空文件夹
    deleted_folders = delete_empty_folders(current_directory)

    # 最终总结
    print(f"\n" + "-" * 30)
    print(f"所有操作完成。")
    print(f"共找到并处理: {total_found} 个文件。")
    print(f"成功删除: {deleted_count} 个文件。")
    if failed_count > 0:
        print(f"失败: {failed_count} 个文件 (详情请查看上面的错误日志)。")
    if deleted_folders > 0:
        print(f"成功删除: {deleted_folders} 个空文件夹。")


if __name__ == "__main__":
    main()
