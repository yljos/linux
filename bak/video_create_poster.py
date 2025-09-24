import os
import subprocess


def main():
    # Provide two predefined paths for user to choose from
    predefined_paths = {
        "1": "/home/huai/data/Downloads/h",
        "2": "/home/huai/data/Downloads/mv",
        "3": "/home/huai/data/Downloads/whitenoise",
    }

    # Display path options
    print("Please select the main video directory path:")
    for key, path in predefined_paths.items():
        print(f"{key}: {path}")

    # Get user selection
    choice = input("Please enter option number (1, 2, or 3): ").strip()

    # Validate user input
    if choice not in predefined_paths:
        print("Invalid option, please run the script again and select 1, 2, or 3.")
        return

    video_dir = predefined_paths[choice]

    # Check if the selected directory is valid
    if not os.path.isdir(video_dir):
        print(f"Error: Video directory '{video_dir}' does not exist.")
        return

    # Traverse the main directory and all its subdirectories
    for root, dirs, files in os.walk(video_dir):
        for file in files:
            # Check if it's a supported video file
            if file.endswith(
                (".mp4", ".ts", ".TS", ".MP4", ".mkv", ".avi", ".mov", ".flv")
            ):
                video_path = os.path.join(root, file)

                # Output image file path, in the same directory as the video file
                output_file = os.path.join(
                    root, f"{os.path.splitext(file)[0]}-poster.jpg"
                )

                # FFmpeg command to generate cover image
                command = [
                    "ffmpeg",
                    "-y",  # Force overwrite output file
                    "-i",
                    video_path,  # Input video path
                    "-ss",
                    "00:00:01",  # Select frame at 1 second, time can be adjusted
                    "-vframes",
                    "1",  # Extract one frame
                    "-q:v",
                    "2",  # Image quality (2 is high quality)
                    output_file,  # Output image path
                ]

                try:
                    subprocess.run(command, check=True)
                    print(f"Cover generation successful: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Cover generation failed: {video_path}. Error: {e}")

    print("Cover generation task completed!")


if __name__ == "__main__":
    main()
