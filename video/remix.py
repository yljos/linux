import subprocess
from pathlib import Path

# Scan and process all MP4 files in the current directory
for file_path in Path.cwd().rglob("*.mp4"):
    # Define a temporary output path
    temp_path = file_path.with_suffix(".tmp.mp4")
    
    print(f"Processing: {file_path.name}")
    
    # Execute ffmpeg to copy streams and move moov atom to the front
    result = subprocess.run([
        "ffmpeg", 
        "-y", 
        "-i", str(file_path), 
        "-c", "copy", 
        "-movflags", "+faststart", 
        str(temp_path)
    ])

    # Atomically replace the original file only if successful
    if result.returncode == 0:
        temp_path.replace(file_path)
    else:
        # Clean up temporary file on failure
        if temp_path.exists():
            temp_path.unlink()
        print(f"Failed: {file_path.name}")

print("Done.")