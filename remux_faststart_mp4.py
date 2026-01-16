import subprocess
import shutil
from pathlib import Path

# --- 可自定义的配置 ---

# 1. 定义需要处理的视频文件扩展名 (使用集合 set 查找速度更快)
VIDEO_EXTENSIONS = {".mp4"}

# 2. 定义存放处理后文件的子目录名称
OUTPUT_FOLDER_NAME = "processed"

# --- 脚本主逻辑 ---


def process_videos_recursively():
    # 检查 ffmpeg
    if not shutil.which("ffmpeg"):
        print("错误：未找到 FFmpeg。请确保已配置环境变量。")
        return

    # 使用 Path 获取当前工作目录
    root_directory = Path.cwd()
    output_root_directory = root_directory / OUTPUT_FOLDER_NAME

    print(f"扫描目录：{root_directory}")
    print(f"输出目录：{output_root_directory}\n")

    # 使用 rglob 进行递归遍历 ('**/*' 代表递归所有子目录和文件)
    for file_path in root_directory.rglob("*"):

        # 1. 跳过文件夹，只处理文件
        if not file_path.is_file():
            continue

        # 2. 关键步骤：跳过输出目录内的文件
        # 如果 output_root_directory 是当前文件路径的父级之一，说明该文件在输出目录中
        if output_root_directory in file_path.parents:
            continue

        # 3. 检查扩展名 (pathlib 的 .suffix 带有点号，例如 .mp4)
        if file_path.suffix.lower() in VIDEO_EXTENSIONS:

            # --- 计算路径 ---
            # 获取相对路径 (例如: sub/video.mp4)
            relative_path = file_path.relative_to(root_directory)
            # 拼接输出路径
            output_path = output_root_directory / relative_path

            # --- 创建目录 ---
            # 直接创建父目录，如果存在则忽略，如果父级不存在则递归创建
            output_path.parent.mkdir(parents=True, exist_ok=True)

            print(f"\n[处理中] -> {relative_path}")

            # 构建命令 (subprocess 接受 Path 对象，但为了最大兼容性可以转为 str)
            command = [
                "ffmpeg",
                "-i",
                str(file_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                "-y",
                str(output_path),
            ]

            try:
                # capture_output=True 是 Python 3.7+ 的新特性，替代 stderr=PIPE
                subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"[成功] ✓ 处理完成: {relative_path}")
            except subprocess.CalledProcessError as e:
                print(f"[失败] X 处理失败: {relative_path}")
                print("FFmpeg 错误信息:")
                print(e.stderr)

    print("\n所有视频文件处理完毕。")


if __name__ == "__main__":
    process_videos_recursively()
