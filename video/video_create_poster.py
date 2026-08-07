import os
import subprocess
import platform
import shutil

def main():
    is_windows = platform.system().lower() == "windows"

    # Define source paths (where real media is)
    if is_windows:
        src_paths = {
            "1": r"Z:\www\media\h",
            "2": r"Z:\www\media\mv",
        }
        # Define destination paths (where strm files are)
        dest_paths = {
            "1": r"Z:\media\h",
            "2": r"Z:\media\mv",
        }
    else:
        src_paths = {
            "1": "/data/www/media/h",
            "2": "/data/www/media/mv",
        }
        dest_paths = {
            "1": "/data/media/h",
            "2": "/data/media/mv",
        }

    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found.")
        return

    for key, path in src_paths.items():
        print(f"{key}: {path}")

    choice = input("Select option (1, 2): ").strip()
    if choice not in src_paths:
        return

    src_dir = src_paths[choice]
    dest_dir = dest_paths[choice]

    if not os.path.isdir(src_dir):
        print(f"Error: {src_dir} not found.")
        return

    startup_info = None
    if is_windows:
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.lower().endswith((".mp4", ".ts", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm")):
                video_path = os.path.join(root, file)
                
                # Calculate relative path to maintain directory structure
                rel_path = os.path.relpath(root, src_dir)
                target_root = os.path.join(dest_dir, rel_path) if rel_path != "." else dest_dir
                
                # Create destination directory if it doesn't exist
                os.makedirs(target_root, exist_ok=True)

                # Output poster in the destination directory next to the strm file
                output_file = os.path.join(target_root, f"{os.path.splitext(file)[0]}-poster.jpg")

                # Skip if poster already exists
                if os.path.exists(output_file):
                    continue

                command = [
                    "ffmpeg",
                    "-y",
                    "-i", video_path,
                    "-ss", "00:00:07",
                    "-vframes", "1",
                    "-q:v", "2",
                    output_file,
                ]

                try:
                    subprocess.run(command, check=True, startupinfo=startup_info, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"Generated: {output_file}")
                except subprocess.CalledProcessError:
                    print(f"Failed: {video_path}")

if __name__ == "__main__":
    main()