import subprocess
import shutil
import json
import time
import sys
from pathlib import Path

# --- Configuration ---
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov",".ts"}
THRESHOLD = 1080
SUFFIX = "_1080p"
COOLDOWN_SECONDS = 60
CPU_THREADS = 2  # Limit to 2 threads for ~50% CPU usage on i5-4570T


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


def get_video_audio_info(file_path):
    """Get width, height, video codec, and audio codec using ffprobe"""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=width,height,codec_name,codec_type",
        "-of",
        "json",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        v_w, v_h, v_codec = 0, 0, "unknown"
        a_codec = "none"  # Default if no audio stream exists
        
        for stream in data.get("streams", []):
            s_type = stream.get("codec_type")
            if s_type == "video" and v_codec == "unknown":
                v_w = int(stream.get("width", 0))
                v_h = int(stream.get("height", 0))
                v_codec = stream.get("codec_name", "unknown")
            elif s_type == "audio" and a_codec == "none":
                a_codec = stream.get("codec_name", "unknown")
                
        return v_w, v_h, v_codec, a_codec
    except:
        return 0, 0, "unknown", "unknown"


def process_videos():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: FFmpeg or ffprobe not found in PATH.")
        return

    root_dir = Path.cwd()
    set_terminal_title("H264 & 1080P Optimizer")

    targets = []
    print(f"[*] Scanning: {root_dir}")

    for file_path in root_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if SUFFIX in file_path.stem:
            continue

        w, h, v_codec, a_codec = get_video_audio_info(file_path)
        short_side = min(w, h)

        needs_downscale = short_side > THRESHOLD
        needs_v_transcode = v_codec != "h264"
        needs_a_transcode = a_codec != "aac" and a_codec != "none"

        if needs_downscale or needs_v_transcode or needs_a_transcode:
            output_path = file_path.with_name(f"{file_path.stem}{SUFFIX}.mp4")
            if not output_path.exists():
                targets.append((file_path, w, h, v_codec, a_codec, output_path, needs_downscale, needs_a_transcode))

    total = len(targets)
    if total == 0:
        print("[i] No files need optimization.")
        return

    print(f"[i] Found {total} targets. Thread limit: {CPU_THREADS}\n" + "-" * 50)

    for index, (src, w, h, v_codec, a_codec, dst, downscale, transcode_audio) in enumerate(targets):
        print(f"[+] Task {index + 1}/{total} | {src.name} (Video: {w}x{h} {v_codec}, Audio: {a_codec})")
        set_terminal_title(f"[{index+1}/{total}] {src.name}")

        filters = ["format=nv12"]
        if downscale:
            s_filter = f"scale=-2:{THRESHOLD}" if w >= h else f"scale={THRESHOLD}:-2"
            filters.append(s_filter)

        audio_args = ["-c:a", "aac", "-b:a", "128k"] if transcode_audio else ["-c:a", "copy"]
        if a_codec == "none":
            audio_args = ["-an"]

        command = [
            "ffmpeg",
            "-y",
            "-threads",
            str(CPU_THREADS),
            "-i",
            str(src),
            "-vf",
            ",".join(filters),
            "-c:v",
            "h264_qsv",
            "-global_quality",
            "20",
        ] + audio_args + [
            "-movflags",
            "+faststart",
            str(dst),
        ]

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
                if "frame=" in line:
                    print(f"\r    {line.strip()}", end="")
            process.wait()
            print(f"\n[✔] Done")
        except Exception as e:
            print(f"\n[!] Error: {e}")

        if index < total - 1:
            print(f"[i] Cooldown: {COOLDOWN_SECONDS}s...")
            time.sleep(COOLDOWN_SECONDS)
            print("-" * 50)

    print("\n[*] All tasks finished.")


if __name__ == "__main__":
    process_videos()