import subprocess
import os

# Traverse all directories starting from the current directory
base_dir = os.getcwd()

for root, dirs, files in os.walk(base_dir):
    folder_name = os.path.basename(root)

    inputs = []
    last_num = 0

    # Scan for files 1.mp4 to 10.mp4 in the current directory level
    for i in range(1, 11):
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
    ts_files = []

    # Step 1: Convert to TS
    for i, video in enumerate(inputs):
        ts_file = f"temp_{i}.ts"
        ts_files.append(ts_file)
        cmd_convert = [
            "ffmpeg",
            "-y",
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

    # Step 2: Merge TS
    concat_string = "concat:" + "|".join(ts_files)
    cmd_merge = [
        "ffmpeg",
        "-y",
        "-i",
        concat_string,
        "-c",
        "copy",
        "-bsf:a",
        "aac_adtstoasc",
        output,
    ]
    subprocess.run(cmd_merge, cwd=root, check=True)

    # Step 3: Cleanup
    for ts in ts_files:
        ts_path = os.path.join(root, ts)
        if os.path.exists(ts_path):
            os.remove(ts_path)
