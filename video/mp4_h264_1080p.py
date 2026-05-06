import subprocess
import shutil
import json
import time
import sys
from pathlib import Path

# --- 配置 ---
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov"}
TARGET_HEIGHT = 1080
SUFFIX = "_1080p"
COOLDOWN_SECONDS = 60  
# 针对 i5-4570T (4线程)，设置为 2 可约占用 50% CPU
CPU_THREADS = 2 

def set_terminal_title(title):
    try:
        import platform
        if platform.system() == "Windows":
            subprocess.run(["title", title], shell=True)
        else:
            sys.stdout.write(f"\x1b]2;{title}\x07")
            sys.stdout.flush()
    except Exception:
        pass

def get_video_info(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=height,codec_name", "-of", "json", str(file_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream = data['streams'][0]
        return int(stream.get('height', 0)), stream.get('codec_name', 'unknown')
    except Exception:
        return 0, "unknown"

def process_videos():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("错误：未找到 FFmpeg 或 ffprobe。")
        return

    root_dir = Path.cwd()
    original_title = "Video Optimizer (Threads Limited)"
    set_terminal_title(original_title)
    
    targets = []
    print(f"[*] 扫描目录: {root_dir}")
    for file_path in root_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if SUFFIX in file_path.stem:
            continue
            
        height, codec = get_video_info(file_path)
        if height > TARGET_HEIGHT or codec != "h264":
            output_path = file_path.with_name(f"{file_path.stem}{SUFFIX}.mp4")
            if not output_path.exists():
                targets.append((file_path, height, codec, output_path))

    total = len(targets)
    if total == 0:
        print("[i] 未发现需要处理的文件。")
        return

    print(f"[i] 待处理: {total} 个，线程限制: {CPU_THREADS}\n" + "-"*50)

    for index, (src, h, codec, dst) in enumerate(targets):
        print(f"[+] 进度 {index + 1}/{total} | {src.name}")
        set_terminal_title(f"[{index+1}/{total}] {src.name}")

        # --- 核心控制：通过 -threads 限制占用 ---
        command = [
            "ffmpeg", "-y",
            "-threads", str(CPU_THREADS), 
            "-i", str(src),
            "-vf", f"format=nv12,scale=-2:'min(ih,{TARGET_HEIGHT})'",
            "-c:v", "h264_qsv",
            "-global_quality", "25",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(dst)
        ]

        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True, 
                encoding="utf-8", 
                errors="replace"
            )

            for line in process.stdout:
                if "frame=" in line:
                    print(f"\r    {line.strip()}", end="")
            process.wait()
            print(f"\n[✔] 完成")
        except Exception as e:
            print(f"\n[!] 出错: {e}")
        finally:
            set_terminal_title(original_title)

        if index < total - 1:
            print(f"[i] 冷却中 ({COOLDOWN_SECONDS}s)...")
            time.sleep(COOLDOWN_SECONDS)
            print("-" * 50)

    print("\n[*] 全部任务执行完毕。")

if __name__ == "__main__":
    process_videos()