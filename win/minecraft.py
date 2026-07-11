import subprocess
import urllib.request
import os

# Configuration
UVX_PATH = r"C:\Users\huai\AppData\Local\Programs\Python\Python312\Scripts\uvx.exe"
MAIN_DIR = r"D:/Minecraft"
BASE_WORK_DIR = r"D:"
EMAIL = "test@outlook.com"
VERSION_URL = "http://10.0.0.21/version.txt"

def get_version(url):
    """Fetch the version string from a URL."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.read().decode("utf-8").strip()
    except Exception as e:
        print(f"Failed to fetch version: {e}")
        return None

def launch_minecraft():
    version = get_version(VERSION_URL)
    if not version:
        return

    # Update work_dir to follow the version number
    work_dir = os.path.join(BASE_WORK_DIR, version)

    command = [
        UVX_PATH, "portablemc",
        "--main-dir", MAIN_DIR,
        "--work-dir", work_dir,
        "start",
        "-l", EMAIL,
        version
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
    except FileNotFoundError:
        print(f"Executable not found at: {UVX_PATH}")

if __name__ == "__main__":
    launch_minecraft()