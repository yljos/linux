import os
import subprocess
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_poster(video_path, output_file, startup_info):
    """Worker function to generate a single poster"""
    # 关键修改：-ss "00:00:02" 必须放在 -i 前面，利用快速输入寻址大幅降低网络 I/O
    command = [
        "ffmpeg",
        "-y",
        "-ss", "00:00:02",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_file,
    ]

    try:
        subprocess.run(
            command, 
            check=True, 
            startupinfo=startup_info, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        return True, output_file
    except subprocess.CalledProcessError:
        return False, video_path

def main():
    is_windows = platform.system().lower() == "windows"

    # Define source paths (where real media is)
    if is_windows:
        src_paths = {
            "1": r"Z:\www\media\h",
            "2": r"Z:\www\media\mv",
        }
        # Define destination paths (where strm files are)
        dest_paths = {
            "1": r"Z:\media\h",
            "2": r"Z:\media\mv",
        }
    else:
        src_paths = {
            "1": "/data/www/media/h",
            "2": "/data/www/media/mv",
        }
        dest_paths = {
            "1": "/data/media/h",
            "2": "/data/media/mv",
        }

    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found.")
        return

    for key, path in src_paths.items():
        print(f"{key}: {path}")

    choice = input("Select option (1, 2): ").strip()
    if choice not in src_paths:
        return

    src_dir = src_paths[choice]
    dest_dir = dest_paths[choice]

    if not os.path.isdir(src_dir):
        print(f"Error: {src_dir} not found.")
        return

    startup_info = None
    if is_windows:
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    print(f"\n[*] Scanning for missing posters in {src_dir} ...")
    
    tasks = []
    # 快速扫描阶段：仅在本地构建任务列表，不调用 ffmpeg
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.lower().endswith((".mp4", ".ts", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm")):
                video_path = os.path.join(root, file)
                
                # Calculate relative path to maintain directory structure
                rel_path = os.path.relpath(root, src_dir)
                target_root = os.path.join(dest_dir, rel_path) if rel_path != "." else dest_dir
                
                # Create destination directory if it doesn't exist
                os.makedirs(target_root, exist_ok=True)

                # Output poster in the destination directory next to the strm file
                output_file = os.path.join(target_root, f"{os.path.splitext(file)[0]}-poster.jpg")

                # Skip if poster already exists
                if not os.path.exists(output_file):
                    tasks.append((video_path, output_file))

    total_tasks = len(tasks)
    if total_tasks == 0:
        print("[i] All posters are already generated.")
        return

    print(f"[*] Found {total_tasks} missing posters. Starting concurrent generation...")

    # 并发执行阶段：使用 10-15 个线程压榨网络空闲时间
    completed = 0
    failed_list = []
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {
            executor.submit(generate_poster, v_path, o_path, startup_info): (v_path, o_path) 
            for v_path, o_path in tasks
        }
        
        for future in as_completed(futures):
            completed += 1
            success, result_path = future.result()
            
            # 实时进度覆盖刷新
            print(f"\r    -> Generating ({completed}/{total_tasks}): {os.path.basename(result_path)[:40].ljust(40)}", end="")
            
            if not success:
                failed_list.append(result_path)

    print("\n" + "-" * 50)
    print(f"[✔] Poster generation finished. Successfully generated: {total_tasks - len(failed_list)}")
    
    if failed_list:
        print(f"[!] Failed to generate posters for {len(failed_list)} files.")
        for f in failed_list:
            print(f"    - {f}")

if __name__ == "__main__":
    main()