import subprocess
import shutil
import json
from pathlib import Path

# --- 配置 ---
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov"}
TARGET_HEIGHT = 1080
SUFFIX = "_1080P"


def get_video_height(file_path):
    """使用 ffprobe 获取视频高度"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=height",
        "-of",
        "json",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return int(data["streams"][0]["height"])
    except:
        return 0


def process_videos():
    # 检查环境
    for tool in ["ffmpeg", "ffprobe"]:
        if not shutil.which(tool):
            print(f"错误：未找到 {tool}，请检查环境变量。")
            return

    root_dir = Path.cwd()
    print(f"正在递归扫描：{root_dir}\n")

    # rglob("*") 递归遍历
    for file_path in root_dir.rglob("*"):
        # 1. 基础过滤：只处理特定后缀的文件
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        # 2. 防止循环处理：跳过已经带后缀的文件
        if SUFFIX in file_path.stem:
            continue

        # 3. 检查分辨率
        height = get_video_height(file_path)
        if height <= TARGET_HEIGHT:
            print(f"[跳过] {height}p 已达标: {file_path.name}")
            continue

        # 4. 构造输出路径 (原目录 + 加上后缀)
        output_path = file_path.with_name(f"{file_path.stem}{SUFFIX}{file_path.suffix}")

        # 如果输出文件已存在，跳过（防止脚本中断重启后重复工作）
        if output_path.exists():
            print(f"[跳过] 文件已存在: {output_path.name}")
            continue

        print(f"\n[处理中] {height}p -> 1080p: {file_path.name}")

        # 5. FFmpeg 命令 (针对 Haswell 优化)
        command = [
            "ffmpeg",
            "-i",
            str(file_path),
            "-vf",
            f"format=nv12,scale=-2:{TARGET_HEIGHT}",  # QSV 必须 nv12 且高度 1080
            "-c:v",
            "h264_qsv",  # 硬件加速编码
            "-global_quality",
            "25",  # 质量平衡点
            "-c:a",
            "copy",  # 音频流拷贝
            "-movflags",
            "+faststart",
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"[成功] ✓: {output_path.name}")
        except subprocess.CalledProcessError as e:
            print(f"[失败] X: {file_path.name}")
            if e.stderr:
                print(f"错误日志: {e.stderr.splitlines()[-1]}")

    print("\n所有任务已完成。")


if __name__ == "__main__":
    process_videos()
