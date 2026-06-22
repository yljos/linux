import subprocess
from pathlib import Path

# Define the output suffix
SUFFIX = "_faststart"

# Scan and process all MP4 files in the current directory
for file_path in Path.cwd().rglob("*.mp4"):
    # Skip files that have already been processed
    if SUFFIX in file_path.stem:
        continue

    output_path = file_path.with_name(f"{file_path.stem}{SUFFIX}.mp4")
    
    print(f"Processing: {file_path.name}")
    
    # Execute ffmpeg to copy streams and move moov atom to the front
    subprocess.run([
        "ffmpeg", 
        "-y", 
        "-i", str(file_path), 
        "-c", "copy", 
        "-movflags", "+faststart", 
        str(output_path)
    ])

print("Done.")