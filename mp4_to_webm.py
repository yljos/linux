import subprocess
import sys
import platform
from pathlib import Path

# --- 配置区 ---

# 1. 定义要查找的视频文件扩展名
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".flv", ".wmv"}

# 2. FFmpeg 参数配置 (保持不变)
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

# 3. 工作指示文件路径配置 (重要：指定到 C:\shutdown\working)
WORKING_FILE_PATH = Path(r"C:\shutdown\working")

# --- 配置区结束 ---

# --- 实用函数 (保持不变) ---


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

    source_path = Path(source_dir).resolve()

    print(f"[*] 开始自动扫描目录及其所有子目录: {source_path}")
    print("-" * 50)

    # ... (循环和转换逻辑保持不变) ...

    for file_path in source_path.rglob("*"):

        # 1. 必须是文件
        if not file_path.is_file():
            continue

        # 2. 检查扩展名
        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        output_path = file_path.with_suffix(".webm")

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

        command = ["ffmpeg", "-i", str(file_path), *FFMPEG_PARAMS, str(output_path)]

        try:
            # 使用 Popen 获取实时输出
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
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

    print("[*] 所有任务处理完毕。")


def main():
    """
    主函数
    """
    source_directory_to_process = "."

    print("=" * 50)
    print("      ffmpeg 全自动转换脚本 (Pathlib 重构版)")
    print(f"      工作指示文件路径: {WORKING_FILE_PATH}")
    print("=" * 50)

    # 确保 C:\shutdown 目录存在
    try:
        WORKING_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(
            f"[!] 错误: 无法创建目录 {WORKING_FILE_PATH.parent}。请检查权限。",
            file=sys.stderr,
        )
        sys.exit(1)

    # 1. 创建工作指示文件
    try:
        # 使用 touch() 创建一个空文件，如果存在则更新时间戳
        WORKING_FILE_PATH.touch()
        print(f"[i] 创建指示文件成功: {WORKING_FILE_PATH}")

        # 2. 执行视频转换
        convert_videos(source_directory_to_process)

    except Exception as e:
        print(f"[!] 脚本运行发生错误: {e}", file=sys.stderr)

    finally:
        # 3. 无论转换成功与否，都要尝试删除工作指示文件
        if WORKING_FILE_PATH.exists():
            try:
                WORKING_FILE_PATH.unlink()
                print(f"[i] 任务完成，删除指示文件: {WORKING_FILE_PATH.name}")
            except Exception as e:
                print(
                    f"[!] 警告: 无法删除指示文件 {WORKING_FILE_PATH.name}: {e}",
                    file=sys.stderr,
                )
        else:
            # 这种情况通常是脚本被强制终止
            pass


if __name__ == "__main__":
    main()
