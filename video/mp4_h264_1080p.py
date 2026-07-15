import subprocess
import shutil
import json
import time
import sys
import os
from pathlib import Path

# --- Configuration ---
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".ts"}
THRESHOLD = 1080
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


def is_faststart(filepath):
    # Check if 'moov' atom appears before 'mdat' atom
    try:
        with open(filepath, "rb") as f:
            while True:
                header = f.read(8)
                if len(header) < 8:
                    break
                size = int.from_bytes(header[:4], "big")
                atom_type = header[4:8]

                if atom_type == b"moov":
                    return True
                if atom_type == b"mdat":
                    return False

                # Skip to the next atom
                f.seek(size - 8, 1)
    except Exception:
        pass
    return False


def get_video_audio_info(file_path):
    # Get width, height, video codec, and audio codec using ffprobe
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
        a_codec = "none"

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


def process_videos(root_dir):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: FFmpeg or ffprobe not found in PATH.")
        return

    set_terminal_title("H264 & 1080P Optimizer")

    targets = []
    print(f"\n[*] Scanning for optimization/transcoding targets: {root_dir}")

    for file_path in root_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        # Skip temporary files
        if file_path.name.endswith(".tmp.mp4"):
            continue

        w, h, v_codec, a_codec = get_video_audio_info(file_path)
        short_side = min(w, h)

        needs_downscale = short_side > THRESHOLD
        needs_v_transcode = v_codec != "h264"
        needs_a_transcode = a_codec != "aac" and a_codec != "none"
        is_transcode = needs_downscale or needs_v_transcode or needs_a_transcode

        # In-place destination (always ends up as .mp4)
        dst = file_path.with_suffix(".mp4")

        if is_transcode:
            targets.append(
                (
                    file_path,
                    w,
                    h,
                    v_codec,
                    a_codec,
                    dst,
                    True,
                    needs_downscale,
                    needs_a_transcode,
                )
            )
        elif file_path.suffix.lower() == ".mp4" and not is_faststart(file_path):
            targets.append(
                (
                    file_path,
                    w,
                    h,
                    v_codec,
                    a_codec,
                    dst,
                    False,
                    False,
                    False,
                )
            )

    total = len(targets)
    if total == 0:
        print("[i] No files need optimization or transcoding.")
        return

    print(f"[i] Found {total} targets. Thread limit: {CPU_THREADS}\n" + "-" * 50)

    for index, (
        src,
        w,
        h,
        v_codec,
        a_codec,
        dst,
        is_transcode,
        downscale,
        transcode_audio,
    ) in enumerate(targets):

        task_desc = f"Video: {w}x{h} {v_codec}, Audio: {a_codec}"
        if not is_transcode:
            task_desc = "Faststart Optimization Only"

        print(f"[+] Task {index + 1}/{total} | {src.name} ({task_desc})")
        set_terminal_title(f"[{index+1}/{total}] {src.name}")

        # Temporary path for atomic replacement processing
        temp_dst = dst.with_suffix(".tmp.mp4")

        if is_transcode:
            filters = ["format=nv12"]
            if downscale:
                s_filter = (
                    f"scale=-2:{THRESHOLD}" if w >= h else f"scale={THRESHOLD}:-2"
                )
                filters.append(s_filter)

            audio_args = (
                ["-c:a", "aac", "-b:a", "128k"] if transcode_audio else ["-c:a", "copy"]
            )
            if a_codec == "none":
                audio_args = ["-an"]

            command = (
                [
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
                ]
                + audio_args
                + [
                    "-movflags",
                    "+faststart",
                    str(temp_dst),
                ]
            )
        else:
            command = [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(src),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(temp_dst),
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

            if process.returncode == 0:
                # Atomically replace destination file
                temp_dst.replace(dst)

                # Cleanup original file if extension changed
                if src != dst and src.exists():
                    src.unlink()
                    print(f"\n[✔] Done (Replaced original {src.name})")
                else:
                    print(f"\n[✔] Done (Replaced original Mp4)")
            else:
                if temp_dst.exists():
                    temp_dst.unlink()
                print(f"\n[!] Failed (ffmpeg exit code {process.returncode})")

        except Exception as e:
            if temp_dst.exists():
                temp_dst.unlink()
            print(f"\n[!] Error: {e}")

        if index < total - 1:
            print(f"[i] Cooldown: {COOLDOWN_SECONDS}s...")
            time.sleep(COOLDOWN_SECONDS)
            print("-" * 50)

    print("\n[*] All optimization/transcoding tasks finished.\n")


def merge_sequential_videos(base_dir):
    print(f"\n[*] Scanning for sequential files to merge in: {base_dir}")
    merged_count = 0
    
    # Traverse all directories starting from the base directory
    for root, dirs, files in os.walk(base_dir):
        folder_name = os.path.basename(root)
        inputs = []
        last_num = 0

        # Scan for files 1.mp4 to 10.mp4 in the current directory level
        for i in range(1, 99):
            file_lower = f"{i}.mp4"
            file_upper = f"{i}.MP4"

            if os.path.exists(os.path.join(root, file_lower)):
                inputs.append(file_lower)
                last_num = i
            elif os.path.exists(os.path.join(root, file_upper)):
                inputs.append(file_upper)
                last_num = i
            else:
                break

        # Skip if there are not enough files to merge in this directory
        if len(inputs) < 2:
            continue

        # Define output file name
        output = f"{folder_name}1-{last_num}.mp4"
        output_path = os.path.join(root, output)
        
        if os.path.exists(output_path):
            continue

        print(f"\n[+] Merging {len(inputs)} files into {output} in {root}")
        ts_files = []

        # Step 1: Convert to TS
        for i, video in enumerate(inputs):
            ts_file = f"temp_{i}.ts"
            ts_files.append(ts_file)
            cmd_convert = [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                video,
                "-c",
                "copy",
                "-bsf:v",
                "h264_mp4toannexb",
                "-f",
                "mpegts",
                ts_file,
            ]
            subprocess.run(cmd_convert, cwd=root, check=True)

        # Step 2: Merge TS with faststart optimization applied immediately
        concat_string = "concat:" + "|".join(ts_files)
        cmd_merge = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            concat_string,
            "-c",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            "-movflags", 
            "+faststart",
            output,
        ]
        subprocess.run(cmd_merge, cwd=root, check=True)

        # Step 3: Cleanup
        for ts in ts_files:
            ts_path = os.path.join(root, ts)
            if os.path.exists(ts_path):
                os.remove(ts_path)
                
        print(f"[✔] Merged successfully: {output}")
        merged_count += 1

    if merged_count == 0:
        print("[i] No files need merging.")
    else:
        print(f"\n[*] All merging tasks finished. Total merged: {merged_count}")


if __name__ == "__main__":
    base_directory = Path.cwd()
    
    # Process/transcode first so merge step receives standardized files
    process_videos(base_directory)
    
    # Merge sequential files after transcoding
    merge_sequential_videos(base_directory)