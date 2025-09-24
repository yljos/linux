import os
import subprocess
import shutil

# --- 可自定义的配置 ---

# 1. 定义需要处理的视频文件扩展名 (可以自行添加)
VIDEO_EXTENSIONS = [".mp4"]

# 2. 定义存放处理后文件的子目录名称
OUTPUT_FOLDER = "processed"

# --- 脚本主逻辑 ---


def process_videos_recursively():
    """
    主函数，递归遍历所有子目录并执行视频批处理任务。
    在输出目录中保持原始的目录结构。
    """
    # 检查 ffmpeg 是否已安装并存在于系统路径中
    if not shutil.which("ffmpeg"):
        print(
            "错误：未找到 FFmpeg。请确保已安装 FFmpeg 并将其添加到了系统的 PATH 环境变量中。"
        )
        return

    # 获取当前脚本所在的根目录
    root_directory = os.getcwd()
    # 定义输出根目录的完整路径
    output_root_directory = os.path.join(root_directory, OUTPUT_FOLDER)

    print(f"将从根目录开始扫描：{root_directory}")
    print(f"处理后的文件将保存在：{output_root_directory}\n")

    # 使用 os.walk 进行递归遍历
    # topdown=True 确保我们可以在进入子目录前将其从遍历列表中移除
    for dirpath, dirnames, filenames in os.walk(root_directory, topdown=True):

        # --- 关键步骤：跳过输出目录本身，避免无限循环或重复处理 ---
        # 如果当前目录是输出目录，或者脚本在输出目录的上层，就跳过
        if (
            os.path.commonpath([dirpath, output_root_directory])
            == output_root_directory
        ):
            continue

        for filename in filenames:
            # 分离文件名和扩展名
            file_base, file_ext = os.path.splitext(filename)

            # 检查文件扩展名是否在我们的目标列表中
            if file_ext.lower() in VIDEO_EXTENSIONS:
                input_path = os.path.join(dirpath, filename)

                # --- 计算并创建对应的输出目录结构 ---
                # 获取当前文件相对于根目录的相对路径
                relative_path = os.path.relpath(input_path, root_directory)
                # 定义输出文件的完整路径，保持目录结构
                output_path = os.path.join(output_root_directory, relative_path)
                # 获取输出文件所在的目录
                output_dir_for_file = os.path.dirname(output_path)

                # 如果输出子目录不存在，则创建它
                if not os.path.exists(output_dir_for_file):
                    os.makedirs(output_dir_for_file)

                print(f"\n[处理中] -> {relative_path}")

                # 构建 ffmpeg 命令
                command = [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-c",
                    "copy",
                    "-movflags",
                    "+faststart",
                    "-y",  # 自动覆盖已存在的文件
                    output_path,
                ]

                # 执行命令
                try:
                    subprocess.run(
                        command, check=True, text=True, stderr=subprocess.PIPE
                    )
                    print(f"[成功] ✓ 处理完成: {relative_path}")
                except subprocess.CalledProcessError as e:
                    print(f"[失败] X 处理失败: {relative_path}")
                    print("FFmpeg 错误信息:")
                    print(e.stderr)

    print("\n所有视频文件处理完毕。")


if __name__ == "__main__":
    process_videos_recursively()
