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
    {
        "filename": "coroutil-fabric-1.21.1-1.3.8.jar",
        "name": "CoroUtil",
        "url": "https://modrinth.com/mod/rLLJ1OZM",
        "version": "1.21.1-1.3.8"
    },
    {
        "filename": "entityculling-fabric-1.10.5-mc1.21.1.jar",
        "name": "EntityCulling",
        "url": "https://modrinth.com/mod/NNAgCjsB",
        "version": "1.10.5"
    },
    {
        "filename": "fabric-api-0.116.15+1.21.1.jar",
        "name": "Fabric API",
        "url": "https://modrinth.com/mod/P7dR8mSH",
        "version": "0.116.15+1.21.1"
    },
    {
        "filename": "gravestones-1.4.2+1.21+A.jar",
        "name": "Gravestones",
        "url": "https://modrinth.com/mod/Heh3BbSv",
        "version": "1.4.2"
    },
    {
        "filename": "pneumonocore-1.3.1+1.21+A.jar",
        "name": "PneumonoCore",
        "url": "https://modrinth.com/mod/ZLKQjA7t",
        "version": "1.3.1"
    },
    {
        "filename": "sodium-fabric-0.8.13-beta.2+mc1.21.1.jar",
        "name": "Sodium",
        "url": "https://modrinth.com/mod/AANobbMI",
        "version": "0.8.13-beta.2+mc1.21.1"
    },
    {
        "filename": "aether-1.21.1-1.5.11-fabric.jar",
        "name": "The Aether",
        "url": "https://modrinth.com/mod/YhmgMVyu",
        "version": "1.5.11"
    },
    {
        "filename": "watut-fabric-1.21.0-1.2.7.jar",
        "name": "What Are They Up To",
        "url": "https://modrinth.com/mod/AtB5mHky",
        "version": "1.21.0-1.2.7"
    },
    {
        "filename": "owo-lib-0.13.0-alpha.15+1.21.jar",
        "name": "oωo",
        "url": "https://modrinth.com/mod/ccKDOlHs",
        "version": "0.13.0-alpha.15+1.21"
    }
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
    """Download and install mods from Modrinth API, and remove unlisted mods."""
    mods_dir = os.path.join(work_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    # Remove unlisted mods
    listed_filenames = {mod["filename"] for mod in MODS_LIST}
    for existing_file in os.listdir(mods_dir):
        if existing_file.endswith(".jar") and existing_file not in listed_filenames:
            try:
                os.remove(os.path.join(mods_dir, existing_file))
                print(f"Removed unlisted mod: {existing_file}")
            except Exception as e:
                print(f"Failed to remove {existing_file}: {e}")

    for mod in MODS_LIST:
        file_path = os.path.join(mods_dir, mod["filename"])
        
        # Skip if file already exists
        if os.path.exists(file_path):
            continue
            
        try:
            # Extract project ID
            project_id = mod["url"].split("/")[-1]
            
            # Fetch versions filtered by loader and game version
            ver_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
            params = {
                "loaders": f'["{loader}"]',
                "game_versions": f'["{mc_version}"]'
            }
            versions = requests.get(ver_url, params=params, impersonate="firefox").json()
            
            # Find the download URL for the target file
            dl_url = None
            if isinstance(versions, list):
                for ver in versions:
                    for file_data in ver.get("files", []):
                        if file_data.get("filename") == mod["filename"]:
                            dl_url = file_data.get("url")
                            break
                    if dl_url:
                        break
                    
            if not dl_url:
                print(f"No compatible version found for {mod['name']}")
                continue
                
            print(f"Downloading {mod['name']}...")
            dl_res = requests.get(dl_url, impersonate="firefox", timeout=600)
            dl_res.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(dl_res.content)
                
        except Exception as e:
            print(f"Error installing {mod['name']}: {e}")


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