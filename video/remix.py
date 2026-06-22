import subprocess
from pathlib import Path

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
                
                if atom_type == b'moov':
                    return True
                if atom_type == b'mdat':
                    return False
                    
                # Skip to the next atom
                f.seek(size - 8, 1)
    except Exception:
        pass
    return False

# Scan and process all MP4 files in the current directory
for file_path in Path.cwd().rglob("*.mp4"):
    # Skip if the file is already faststart optimized
    if is_faststart(file_path):
        continue

    # Define a temporary output path
    temp_path = file_path.with_suffix(".tmp.mp4")
    
    print(f"Processing: {file_path.name}")
    
    # Execute ffmpeg to copy streams and move moov atom to the front
    result = subprocess.run([
        "ffmpeg", 
        "-y",
        "-v", "error",
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