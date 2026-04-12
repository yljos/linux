import subprocess
import sys
import platform
import json
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov"}

FFMPEG_PARAMS = [
    "-c:v", "libx264",
    "-preset", "superfast",
    "-crf", "18",
    "-c:a", "copy"
]

def set_terminal_title(title):
    try:
        if platform.system() == "Windows":
            subprocess.run(["title", title], shell=True)
        else:
            sys.stdout.write(f"\x1b]2;{title}\x07")
            sys.stdout.flush()
    except Exception:
        pass

def get_codec(file_path):
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-select_streams", "v:0", 
        "-show_entries", "stream=codec_name", 
        "-of", "json", 
        str(file_path)
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        data = json.loads(output)
        return data["streams"][0]["codec_name"]
    except Exception:
        return "unknown"

def convert_videos(source_dir):
    original_title = "Non-H264 to H264 Auto Converter"
    set_terminal_title(original_title)
    source_path = Path(source_dir).resolve()

    print(f"[*] Scanning directory: {source_path}")
    print("-" * 50)

    for file_path in source_path.rglob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        codec = get_codec(file_path)
        if codec == "h264":
            continue

        output_path = file_path.with_name(f"{file_path.stem}_h264.mp4")

        if output_path.exists() or file_path.name.endswith("_h264.mp4"):
            print(f"[i] Skip: Output exists {output_path.name}")
            print("-" * 50)
            continue

        print(f"[+] Processing: {file_path.name} (Found {codec} codec)")
        
        try:
            display_path = output_path.relative_to(source_path)
        except ValueError:
            display_path = output_path
            
        print(f"    -> Output to: {display_path}")
        set_terminal_title(f"Converting: {file_path.name}")

        command = ["ffmpeg", "-i", str(file_path), *FFMPEG_PARAMS, str(output_path)]

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
            )

            for line in process.stdout:
                print(f"    [{file_path.name}] {line.strip()}")

            process.wait()

            if process.returncode == 0:
                print(f"[✔] Success: {file_path.name}")
            else:
                print(f"[!] Failed: {file_path.name} (Code: {process.returncode})", file=sys.stderr)

        except FileNotFoundError:
            print("[!] Error: ffmpeg not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[!] Unknown error: {e}", file=sys.stderr)
        finally:
            set_terminal_title(original_title)

        print("-" * 50)

    print("[*] All tasks completed.")

def main():
    source_directory_to_process = "."

    print("=" * 50)
    print("      Non-H264 to H264 Auto Converter")
    print("=" * 50)

    try:
        convert_videos(source_directory_to_process)
    except Exception as e:
        print(f"[!] Script error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()