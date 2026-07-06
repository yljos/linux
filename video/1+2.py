import subprocess
import os

# Define input files and output file
inputs = ['1.mp4', '2.mp4']
output = 'merged.mp4'
ts_files = []

# Step 1: Convert each MP4 to a temporary TS file without re-encoding
for i, video in enumerate(inputs):
    ts_file = f"temp_{i}.ts"
    ts_files.append(ts_file)
    cmd_convert = [
        'ffmpeg',
        '-y',
        '-i', video,
        '-c', 'copy',                   # Copy streams
        '-bsf:v', 'h264_mp4toannexb',   # Bitstream filter for H.264
        '-f', 'mpegts',                 # Output format
        ts_file
    ]
    subprocess.run(cmd_convert, check=True)

# Step 2: Concatenate the TS files and output as MP4
concat_string = 'concat:' + '|'.join(ts_files)
cmd_merge = [
    'ffmpeg',
    '-y',
    '-i', concat_string,
    '-c', 'copy',                   # Copy streams
    '-bsf:a', 'aac_adtstoasc',      # Bitstream filter for AAC audio
    output
]
subprocess.run(cmd_merge, check=True)

# Step 3: Clean up temporary TS files
for ts in ts_files:
    if os.path.exists(ts):
        os.remove(ts)