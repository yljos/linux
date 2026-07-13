import subprocess
import os
from curl_cffi import requests

# Configuration
UVX_PATH = r"C:\Users\dayao\AppData\Local\Programs\Python\Python312\Scripts\uvx.exe"
MAIN_DIR = r"D:/Minecraft"
BASE_WORK_DIR = r"D:"
EMAIL = "dayao"
VERSION_URL = "https://www.com/version.txt"

def get_version(url):
    """Fetch the version string from a URL with Firefox fingerprinting."""
    try:
        # Use curl_cffi to impersonate Firefox
        response = requests.get(url, timeout=5, impersonate="firefox")
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Failed to fetch version: {e}")
        return None

def launch_minecraft():
    version_data = get_version(VERSION_URL)
    if not version_data:
        return

    # Parse loader and version (e.g., "forge,1.12.2" or "fabric,1.12.2" or "vanilla,1.12.2")
    if "," in version_data:
        loader, mc_version = version_data.split(",", 1)
        loader = loader.strip().lower()
        mc_version = mc_version.strip()
    else:
        # Default to vanilla if no comma is found
        loader, mc_version = "vanilla", version_data.strip()

    # Share the same version directory (e.g., D:\1.12.2) for all loaders
    work_dir = os.path.join(BASE_WORK_DIR, mc_version)

    # Format the target version argument for portablemc
    if loader in ["vanilla", "原版"]:
        target_version = mc_version
    else:
        target_version = f"{loader}:{mc_version}"

    command = [
        UVX_PATH, "portablemc",
        "--main-dir", MAIN_DIR,
        "--work-dir", work_dir,
        "start",
        "-l", EMAIL,
        target_version
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
    except FileNotFoundError:
        print(f"Executable not found at: {UVX_PATH}")

if __name__ == "__main__":
    launch_minecraft()