import subprocess
import os
from curl_cffi import requests

# Configuration
UVX_PATH = r"C:\Users\dayao\AppData\Local\Programs\Python\Python312\Scripts\uvx.exe"
MAIN_DIR = r"D:/Minecraft"
BASE_WORK_DIR = r"D:"
EMAIL = "dayao"
VERSION_URL = "https://www.127.0.0.1.com/version.txt"

# Target server configuration (Leave None to disable auto-connect)
SERVER_ADDR = "127.0.0.1"  # Example server address
SERVER_PORT = "25565"           # Default Minecraft port

# Target language configuration (Leave None to use default/previous language)
# e.g., "zh_cn" for Simplified Chinese, "en_us" for English
GAME_LANG = "zh_cn"             

def get_version(url):
    """Fetch the version string from a URL with Firefox fingerprinting."""
    try:
        response = requests.get(url, timeout=5, impersonate="firefox")
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Failed to fetch version: {e}")
        return None

def set_game_language(work_dir, lang):
    """Ensure the target language is set in options.txt before launching."""
    options_path = os.path.join(work_dir, "options.txt")
    lang_line = f"lang:{lang}\n"
    
    # Create work_dir if it doesn't exist yet
    os.makedirs(work_dir, exist_ok=True)
    
    if not os.path.exists(options_path):
        with open(options_path, "w", encoding="utf-8") as f:
            f.write(lang_line)
        return

    # Read and update existing options.txt
    with open(options_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    lang_found = False
    for i, line in enumerate(lines):
        if line.startswith("lang:"):
            lines[i] = lang_line
            lang_found = True
            break

    if not lang_found:
        lines.append(lang_line)

    with open(options_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def launch_minecraft():
    version_data = get_version(VERSION_URL)
    if not version_data:
        return

    if "," in version_data:
        loader, mc_version = version_data.split(",", 1)
        loader = loader.strip().lower()
        mc_version = mc_version.strip()
    else:
        loader, mc_version = "vanilla", version_data.strip()

    work_dir = os.path.join(BASE_WORK_DIR, mc_version)

    # Automatically configure language before starting
    if GAME_LANG:
        set_game_language(work_dir, GAME_LANG)

    if loader in ["vanilla", "原版"]:
        target_version = mc_version
    else:
        target_version = f"{loader}:{mc_version}"

    # Build startup command
    command = [
        UVX_PATH, "portablemc",
        "--main-dir", MAIN_DIR,
        "--work-dir", work_dir,
        "start",
        "-u", EMAIL
    ]

    # Append server arguments if specified
    if SERVER_ADDR:
        command.extend(["-s", SERVER_ADDR])
        if SERVER_PORT:
            command.extend(["-p", SERVER_PORT])

    command.append(target_version)

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
    except FileNotFoundError:
        print(f"Executable not found at: {UVX_PATH}")

if __name__ == "__main__":
    launch_minecraft()