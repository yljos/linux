import subprocess
import os
import sys
from curl_cffi import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
MAIN_DIR = r"D:/Minecraft"
BASE_WORK_DIR = r"D:"
EMAIL = "dayao"
UPDATE_URL = (
    "https://raw.githubusercontent.com/yljos/linux/refs/heads/main/win/minecraft.py"
)

# Strict environment variables loading
VERSION_URL = os.environ["VERSION_URL"]
SERVER_ADDR = os.environ["SERVER_ADDR"]
SERVER_PORT = os.environ["SERVER_PORT"]
GAME_LANG = "zh_cn"

# Proxy configuration
UPDATE_PROXIES = {
    "http": "socks5://127.0.0.1:12138",
    "https": "socks5://127.0.0.1:12138",
}

# Mod list
MODS_LIST = [
    "EntityCulling",
    "Fabric API",
    "Gravestones",
    "PneumonoCore",
    "Sodium",
    "The Aether",
    "oωo"
]

def update_self():
    """Fetch the latest script from the server and restart if updated."""
    try:
        response = requests.get(UPDATE_URL, timeout=5, impersonate="firefox")
    except Exception as e:
        print(f"Direct update failed ({e}), attempting with proxy...")
        try:
            response = requests.get(
                UPDATE_URL, timeout=5, impersonate="firefox", proxies=UPDATE_PROXIES
            )
        except Exception as proxy_e:
            print(f"Proxy update failed: {proxy_e}")
            return

    try:
        response.raise_for_status()
        new_code = response.text

        with open(__file__, "r", encoding="utf-8") as f:
            current_code = f.read()

        if new_code != current_code and new_code.strip():
            with open(__file__, "w", encoding="utf-8") as f:
                f.write(new_code)
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"Failed to process update: {e}")


def get_version(url):
    """Fetch the version string from a URL with Firefox fingerprinting."""
    try:
        proxies = {"http": "", "https": ""}
        response = requests.get(url, timeout=5, impersonate="firefox", proxies=proxies)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"Failed to fetch version: {e}")
        return None


def set_game_language(work_dir, lang):
    """Ensure the target language is set in options.txt."""
    options_path = os.path.join(work_dir, "options.txt")
    lang_line = f"lang:{lang}\n"
    os.makedirs(work_dir, exist_ok=True)

    if not os.path.exists(options_path):
        with open(options_path, "w", encoding="utf-8") as f:
            f.write(lang_line)
        return

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


def install_mods(work_dir, mc_version, loader):
    """Download and install mods from Modrinth API."""
    mods_dir = os.path.join(work_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    for mod in MODS_LIST:
        try:
            # Search for the mod project id
            search_url = f"https://api.modrinth.com/v2/search?query={mod}&limit=1"
            search_res = requests.get(search_url, impersonate="firefox").json()
            if not search_res.get("hits"):
                print(f"Mod not found: {mod}")
                continue
            
            project_id = search_res["hits"][0]["project_id"]
            
            # Fetch compatible versions
            ver_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
            params = {"game_versions": f'["{mc_version}"]', "loaders": f'["{loader}"]'}
            versions = requests.get(ver_url, params=params, impersonate="firefox").json()
            
            if not versions:
                print(f"No compatible version for {mod}")
                continue
                
            # Get the first matching file
            file_data = versions[0]["files"][0]
            file_path = os.path.join(mods_dir, file_data["filename"])
            
            # Download if not exists
            if not os.path.exists(file_path):
                print(f"Downloading {mod}...")
                dl_res = requests.get(file_data["url"], impersonate="firefox")
                with open(file_path, "wb") as f:
                    f.write(dl_res.content)
                    
        except Exception as e:
            print(f"Error installing {mod}: {e}")


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

    if loader in ["vanilla", "原版"]:
        work_dir = os.path.join(BASE_WORK_DIR, mc_version)
    else:
        work_dir = os.path.join(BASE_WORK_DIR, f"{mc_version}_{loader}")

    if GAME_LANG:
        set_game_language(work_dir, GAME_LANG)

    # Install mods if not vanilla
    if loader not in ["vanilla", "原版"]:
        install_mods(work_dir, mc_version, loader)

    if loader in ["vanilla", "原版"]:
        target_version = mc_version
    else:
        target_version = f"{loader}:{mc_version}"

    command = [
        "uvx",
        "portablemc",
        "--main-dir",
        MAIN_DIR,
        "--work-dir",
        work_dir,
        "start",
        "-u",
        EMAIL,
    ]

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
        print("Executable not found: uvx")


if __name__ == "__main__":
    update_self()
    launch_minecraft()