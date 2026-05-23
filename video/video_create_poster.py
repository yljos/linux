import os
import subprocess
import platform  # 用于检测操作系统
import shutil  # 用于检查 ffmpeg 是否存在


def main():
    # 检测当前是否为 Windows 系统
    is_windows = platform.system().lower() == "windows"

    # ================= 路径配置 =================
    if is_windows:
        # Windows 环境下的路径 (注意前面加 r)
        print("🖥️ 检测到系统: Windows")
        predefined_paths = {
            "1": r"D:\Downloads\h",
            "2": r"Z:\media\mv",  # 你刚才提到的挂载盘
        }
    else:
        # Linux 环境下的路径 (保留你原来的)
        print("🐧 检测到系统: Linux")
        predefined_paths = {
            "1": "/home/huai/data/Downloads/h",
            "2": "/home/huai/data/media/mv",
        }
    # ===========================================

    # 检查 ffmpeg 是否可用
    if not shutil.which("ffmpeg"):
        print("❌ 错误: 未找到 ffmpeg 命令，请先安装或配置环境变量。")
        if is_windows:
            input("按回车键退出...")
        return

    # Display path options
    print("Please select the main video directory path:")
    for key, path in predefined_paths.items():
        print(f"{key}: {path}")

    # Get user selection
    choice = input("Please enter option number (1, 2): ").strip()

    # Validate user input
    if choice not in predefined_paths:
        print("Invalid option, please run the script again and select 1, 2")
        return

    video_dir = predefined_paths[choice]

    # Check if the selected directory is valid
    if not os.path.isdir(video_dir):
        print(f"Error: Video directory '{video_dir}' does not exist.")
        return

    # Windows 特有的设置：隐藏弹出的黑框
    startup_info = None
    if is_windows:
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Traverse the main directory and all its subdirectories
    for root, dirs, files in os.walk(video_dir):
        for file in files:
            # Check if it's a supported video file (使用 .lower() 忽略大小写差异)
            if file.lower().endswith(
                (".mp4", ".ts", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm")
            ):
                video_path = os.path.join(root, file)

                # Output image file path, in the same directory as the video file
                output_file = os.path.join(
                    root, f"{os.path.splitext(file)[0]}-poster.jpg"
                )

                # FFmpeg command to generate cover image
                command = [
                    "ffmpeg",
                    "-y",  # Force overwrite output file
                    "-i",
                    video_path,  # Input video path
                    "-ss",
                    "00:00:07",  # Select frame at 1 second, time can be adjusted
                    "-vframes",
                    "1",  # Extract one frame
                    "-q:v",
                    "2",  # Image quality (2 is high quality)
                    output_file,  # Output image path
                ]

                try:
                    # 增加 startupinfo 参数兼容 Windows
                    subprocess.run(command, check=True, startupinfo=startup_info)
                    print(f"Cover generation successful: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Cover generation failed: {video_path}. Error: {e}")

    print("Cover generation task completed!")
    if is_windows:
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
