import subprocess
import shutil
import json
import time
import sys
import platform
from pathlib import Path

# --- 配置 ---
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov"}
TARGET_HEIGHT = 1080
SUFFIX = "_1080p"
COOLDOWN_SECONDS = 300  # 任务间冷却5分钟

def set_terminal_title(title):
    try:
        if platform.system() == "Windows":
            subprocess.run(["title", title], shell=True)
        else:
            sys.stdout.write(f"\x1b]2;{title}\x07")
            sys.stdout.flush()
    except Exception:
        pass

def get_video_info(file_path):
    """获取视频高度和编码格式"""
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
    for tool in ["ffmpeg", "ffprobe"]:
        if not shutil.which(tool):
            print(f"错误：未找到 {tool}，请检查环境变量。")
            return

    root_dir = Path.cwd()
    original_title = "Video 1080P/H264 Optimizer"
    set_terminal_title(original_title)
    
    # 预扫描目标
    targets = []
    print(f"[*] 正在扫描目录: {root_dir}")
    for file_path in root_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if SUFFIX in file_path.stem:
            continue
            
        height, codec = get_video_info(file_path)
        # 判断是否需要处理：高度 > 1080 或 编码不是 h264
        if height > TARGET_HEIGHT or codec != "h264":
            output_path = file_path.with_name(f"{file_path.stem}{SUFFIX}.mp4")
            if not output_path.exists():
                targets.append((file_path, height, codec, output_path))

    total = len(targets)
    if total == 0:
        print("[i] 没有发现需要转换的文件。")
        return

    print(f"[i] 找到 {total} 个待处理文件\n" + "-"*50)

    for index, (src, h, codec, dst) in enumerate(targets):
        print(f"[+] 进度 {index + 1}/{total}")
        print(f"    输入: {src.name} ({h}p, {codec})")
        print(f"    输出: {dst.name}")
        
        set_terminal_title(f"Processing: {src.name}")

        # 构建命令：使用 QSV 硬件编码，高度限制为 1080，音频流拷贝
        # scale=-2:'min(ih,1080)' 确保高度不超过1080且宽度为偶数
        command = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", f"format=nv12,scale=-2:'min(ih,{TARGET_HEIGHT})'",
            "-c:v", "h264_qsv",
            "-global_quality", "25",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(dst)
        ]

        try:
            # 实时打印 ffmpeg 输出 (从第二个脚本集成的逻辑)
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, encoding="utf-8", errors="replace"
            )
            for line in process.stdout:
                if "frame=" in line: # 只显示进度行，防止刷屏
                    print(f"\r    {line.strip()}", end="")
            process.wait()
            print(f"\n[✔] 成功: {src.name}")
        except Exception as e:
            print(f"\n[!] 错误: {src.name}\n{e}")
        finally:
            set_terminal_title(original_title)

        # 任务间冷却
        if index < total - 1:
            print(f"[i] 冷却中：等待 {COOLDOWN_SECONDS // 60} 分钟...")
            time.sleep(COOLDOWN_SECONDS)
            print("-"*50)

    print("\n[*] 所有任务已完成。")

if __name__ == "__main__":
    process_videos()