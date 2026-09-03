# /// script
# dependencies = [
#   "curl-cffi",
#   "python-dotenv"
# ]
# ///
import subprocess
import os
import sys
import platform
from curl_cffi import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Cross-platform configuration
if platform.system() == "Windows":
    MAIN_DIR = os.getenv("MC_MAIN_DIR", r"D:/Minecraft")
    BASE_WORK_DIR = os.getenv("MC_WORK_DIR", r"D:")
else:
    MAIN_DIR = os.getenv("MC_MAIN_DIR", os.path.expanduser("~/Minecraft"))
    BASE_WORK_DIR = os.getenv("MC_WORK_DIR", os.path.expanduser("~"))

EMAIL = os.environ["EMAIL"]
UPDATE_URL = (
    "https://raw.githubusercontent.com/yljos/linux/refs/heads/main/minecraft/minecraft.py"
)
JSON_BASE_URL = "https://raw.githubusercontent.com/yljos/linux/refs/heads/main/minecraft"

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


def fetch_url(url, timeout=10, **kwargs):
    """Fetch URL with direct connection, fallback to proxy."""
    try:
        return requests.get(url, timeout=timeout, impersonate="firefox", **kwargs)
    except Exception as e:
        print(f"Direct connection failed ({e}), using proxy...")
        return requests.get(
            url,
            timeout=timeout + 5,
            impersonate="firefox",
            proxies=UPDATE_PROXIES,
            **kwargs
        )


def update_self():
    """Fetch the latest script from the server and restart if updated."""
    try:
        response = fetch_url(UPDATE_URL, timeout=5)
        response.raise_for_status()
        new_code = response.text

        # Anti-bricking validation
        if "def update_self():" not in new_code or "import " not in new_code:
            print("Update payload invalid, aborting update.")
            return

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
    """Fetch mod list and install mods, remove unlisted ones."""
    json_filename = f"{mc_version}_{loader}.json"
    json_url = f"{JSON_BASE_URL}/{json_filename}"
    
    print(f"Fetching mod list from: {json_url}")
    try:
        response = fetch_url(json_url, timeout=10)
        response.raise_for_status()
        mods_list = response.json()
    except Exception as e:
        print(f"Failed to process mod list from {json_url}: {e}")
        return

    mods_dir = os.path.join(work_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    # Remove unlisted mods
    listed_filenames = {mod["filename"] for mod in mods_list}
    for existing_file in os.listdir(mods_dir):
        if existing_file.endswith(".jar") and existing_file not in listed_filenames:
            try:
                os.remove(os.path.join(mods_dir, existing_file))
                print(f"Removed unlisted mod: {existing_file}")
            except Exception as e:
                print(f"Failed to remove {existing_file}: {e}")

    for mod in mods_list:
        file_path = os.path.join(mods_dir, mod["filename"])
        
        # Skip if file already exists
        if os.path.exists(file_path):
            continue
            
        try:
            project_id = mod["url"].split("/")[-1]
            dl_url = None

            # Platform routing based on URL
            if "curseforge.com" in mod["url"]:
                # Fetch from CurseForge via api.curse.tools proxy
                ver_url = f"https://api.curse.tools/v1/cf/mods/{project_id}/files"
                cf_res = fetch_url(ver_url, timeout=15)
                cf_res.raise_for_status()
                
                for file_data in cf_res.json().get("data", []):
                    if file_data.get("fileName") == mod["filename"]:
                        dl_url = file_data.get("downloadUrl")
                        # Fallback for CDN construction if downloadUrl is null
                        if not dl_url:
                            fid = str(file_data.get("id"))
                            dl_url = f"https://edge.forgecdn.net/files/{fid[:4]}/{fid[4:]}/{mod['filename']}"
                        break
            else:
                # Fetch versions filtered by loader and game version (Modrinth)
                ver_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
                params = {
                    "loaders": f'["{loader}"]',
                    "game_versions": f'["{mc_version}"]'
                }
                versions_res = fetch_url(ver_url, timeout=10, params=params)
                versions_res.raise_for_status()
                versions = versions_res.json()
                
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
            dl_res = fetch_url(dl_url, timeout=600)
            dl_res.raise_for_status()
            
            # Write to .tmp first to prevent corruption, cross-platform atomic replace
            tmp_path = file_path + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(dl_res.content)
            os.replace(tmp_path, file_path)
                
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
        "-l",
        EMAIL,
    ]

    if SERVER_ADDR:
        command.extend(["-s", SERVER_ADDR])
        if SERVER_PORT:
            command.extend(["-p", SERVER_PORT])

    command.append(target_version)

    # Hand over process control to portablemc
    print("Handing over to portablemc...")
    sys.stdout.flush()

    if platform.system() == "Windows":
        # Windows lacks true execvp, fallback to subprocess
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred: {e}")
        except FileNotFoundError:
            print("Executable not found: uvx")
    else:
        # POSIX (Linux/macOS): True process replacement
        try:
            os.execvp("uvx", command)
        except FileNotFoundError:
            print("Executable not found: uvx")


if __name__ == "__main__":
    update_self()
    launch_minecraft()