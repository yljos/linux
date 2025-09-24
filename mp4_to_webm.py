#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import platform

# --- 配置区 ---

# 1. 定义要查找的视频文件扩展名 (可以根据需要添加或删除)
#    使用小写形式，脚本会自动忽略大小写
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv")

# 2. FFmpeg 参数配置
#    您可以在这里修改 CRF, cpu-used, 音频码率等参数
FFMPEG_PARAMS = [
    "-c:v",
    "libvpx-vp9",
    "-crf",
    "33",
    "-b:v",
    "0",
    "-speed",
    "2",
    "-threads",
    "2",
    "-row-mt",
    "1",
    "-c:a",
    "libopus",
    "-b:a",
    "96k",
]
# --- 配置区结束 ---


def set_terminal_title(title):
    """
    根据操作系统设置终端窗口的标题。
    """
    try:
        if platform.system() == "Windows":
            os.system(f"title {title}")
        else:
            # 适用于大多数 Linux/macOS 终端
            sys.stdout.write(f"\x1b]2;{title}\x07")
            sys.stdout.flush()
    except Exception:
        # 在某些环境下（如非 TTY 输出），此操作可能会失败，但我们可以安全地忽略它
        pass


def convert_videos(source_dir):
    """
    遍历源目录及其子目录，查找视频文件并将其在原地转换为 .webm 格式。
    """
    original_title = "FFmpeg 全自动转换脚本"
    set_terminal_title(original_title)
    abs_source_dir = os.path.abspath(source_dir)
    print(f"[*] 开始自动扫描目录及其所有子目录: {abs_source_dir}")
    print("-" * 50)

    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            if filename.lower().endswith(VIDEO_EXTENSIONS):
                input_path = os.path.join(root, filename)
                base, ext = os.path.splitext(input_path)
                output_path = base + ".webm"

                if os.path.exists(output_path):
                    print(f"[i] 跳过: 输出文件已存在 {output_path}")
                    print("-" * 50)
                    continue

                print(f"[+] 开始处理: {input_path}")
                print(f"    -> 输出到: {output_path}")

                # --- 核心改动 1: 设置终端标题 ---
                set_terminal_title(f"正在转换: {filename}")

                command = ["ffmpeg", "-i", input_path, *FFMPEG_PARAMS, output_path]

                try:
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        encoding="utf-8",
                    )

                    # --- 核心改动 2: 为 FFmpeg 的每一行输出添加前缀 ---
                    for line in process.stdout:
                        print(f"    [{filename}] {line.strip()}")

                    process.wait()

                    if process.returncode == 0:
                        print(f"[✔] 成功: {filename}")
                    else:
                        print(
                            f"[!] 失败: {filename} (ffmpeg 返回代码: {process.returncode})",
                            file=sys.stderr,
                        )

                except FileNotFoundError:
                    print("[!] 错误: ffmpeg 命令未找到。", file=sys.stderr)
                    print(
                        "    请确保 ffmpeg 已安装并已添加到系统的 PATH 环境变量中。",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                except Exception as e:
                    print(f"[!] 发生未知错误: {e}", file=sys.stderr)
                finally:
                    # 确保无论成功还是失败，都重置终端标题
                    set_terminal_title(original_title)

                print("-" * 50)


def main():
    """
    (全自动版)
    主函数，直接处理当前目录。
    """
    source_directory_to_process = "."

    print("=" * 50)
    print("      ffmpeg 全自动转换脚本已启动")
    print("      将在当前目录及其子目录中查找视频文件")
    print("      (增强状态显示版)")
    print("=" * 50)

    convert_videos(source_directory_to_process)
    print("[*] 所有任务处理完毕。")


if __name__ == "__main__":
    main()
