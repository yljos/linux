#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys
import platform
from pathlib import Path

# --- 配置区 ---

# 1. 定义要查找的视频文件扩展名
#    pathlib 的 .suffix 包含点号 (例如 .mp4)
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"}

# 2. FFmpeg 参数配置
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
            subprocess.run(["title", title], shell=True)
        else:
            # 适用于大多数 Linux/macOS 终端
            sys.stdout.write(f"\x1b]2;{title}\x07")
            sys.stdout.flush()
    except Exception:
        pass


def convert_videos(source_dir):
    """
    使用 pathlib 遍历目录并转换视频。
    """
    original_title = "FFmpeg 全自动转换脚本 (Pathlib版)"
    set_terminal_title(original_title)

    # 将输入转换为 Path 对象并解析绝对路径
    source_path = Path(source_dir).resolve()

    print(f"[*] 开始自动扫描目录及其所有子目录: {source_path}")
    print("-" * 50)

    # 使用 rglob('*') 递归遍历所有文件和文件夹
    for file_path in source_path.rglob("*"):

        # 1. 必须是文件
        if not file_path.is_file():
            continue

        # 2. 检查扩展名 (.suffix 包含点号，例如 .mp4)
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        # --- Pathlib 核心优势：轻松替换后缀 ---
        # input_path 就是 file_path 本身
        output_path = file_path.with_suffix(".webm")

        # 检查是否存在
        if output_path.exists():
            print(f"[i] 跳过: 输出文件已存在 {output_path.name}")
            print("-" * 50)
            continue

        print(f"[+] 开始处理: {file_path.name}")
        # relative_to 可以显示相对于起始目录的路径，看起来更整洁
        try:
            display_path = output_path.relative_to(source_path)
        except ValueError:
            display_path = output_path
        print(f"    -> 输出到: {display_path}")

        set_terminal_title(f"正在转换: {file_path.name}")

        # 构建命令 (subprocess 需要字符串路径，所以这里做一次转换)
        command = ["ffmpeg", "-i", str(file_path), *FFMPEG_PARAMS, str(output_path)]

        try:
            # 使用 Popen 获取实时输出
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",  # 防止编码错误导致脚本崩溃
            )

            # 逐行读取输出并添加前缀
            for line in process.stdout:
                print(f"    [{file_path.name}] {line.strip()}")

            process.wait()

            if process.returncode == 0:
                print(f"[✔] 成功: {file_path.name}")
            else:
                print(
                    f"[!] 失败: {file_path.name} (代码: {process.returncode})",
                    file=sys.stderr,
                )

        except FileNotFoundError:
            print("[!] 错误: 未找到 ffmpeg，请检查环境变量。", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[!] 发生未知错误: {e}", file=sys.stderr)
        finally:
            set_terminal_title(original_title)

        print("-" * 50)


def main():
    """
    主函数
    """
    # 默认为当前目录 (.)
    source_directory_to_process = "."

    print("=" * 50)
    print("      ffmpeg 全自动转换脚本 (Pathlib 重构版)")
    print("      将在当前目录及其子目录中查找视频文件")
    print("=" * 50)

    convert_videos(source_directory_to_process)
    print("[*] 所有任务处理完毕。")


if __name__ == "__main__":
    main()
