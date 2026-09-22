import os
import time
import subprocess
import ctypes
from dotenv import load_dotenv
from curl_cffi import requests

# Configuration
UPDATE_INTERVAL = 3600  # 1 hour in seconds
MIHOMO_DIR = r"c:\clash"  # Runtime and config directory
TMP_DIR = os.path.join(MIHOMO_DIR, "tmp")  # Temporary directory for downloads
MIHOMO_CONFIG = os.path.join(MIHOMO_DIR, "config.yaml")
MIHOMO_EXE = r"C:\Program Files\clash\mihomo-windows-amd64-v3.exe"  # Kernel executable path


def is_admin():
    """Check for administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def restart_service(service_name):
    """Restart the specified service"""
    print(f"Attempting to restart service: {service_name} ...")
    try:
        subprocess.run(["net", "stop", service_name], check=False, shell=True)
        time.sleep(2)
        subprocess.run(["net", "start", service_name], check=True, shell=True)
        print(f"[Success] Service {service_name} restarted.")
    except subprocess.CalledProcessError as e:
        print(f"[Failed] Service startup failed: {e}")
    except Exception as e:
        print(f"Unknown error during service restart: {e}")


def test_mihomo_config(config_path):
    """Test the validity of the mihomo configuration file using mihomo itself"""
    print("Testing downloaded configuration using mihomo...")
    if not os.path.exists(MIHOMO_EXE):
        print(f"[Warning] Cannot find {MIHOMO_EXE}. Skipping config validation via mihomo.")
        return None

    try:
        # Run mihomo test: -d for runtime directory, -f for config file
        result = subprocess.run(
            [MIHOMO_EXE, "-t", "-d", MIHOMO_DIR, "-f", config_path],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        output_lower = result.stdout.lower()
        if result.returncode == 0 and (
           "test is successful" in output_lower
        ):
             print("[Success] Configuration is valid.")
             return True
        else:
             print(f"[Error] Configuration validation failed. Output:\n{result.stdout}\n{result.stderr}")
             return False

    except Exception as e:
         print(f"[Error] Failed to execute mihomo test: {e}")
         return None


def perform_update():
    """Execute the update process"""
    load_dotenv(override=True)
    url = os.getenv("URL")

    user_agent = os.getenv("USER_AGENT", "clash")
    headers = {"User-Agent": user_agent}

    if not url:
        print("Error: URL not found in .env, skipping this update.")
        return False

    service_name = "clash"
    save_path = MIHOMO_CONFIG
    
    # Place temp file in the dedicated tmp directory
    temp_path = os.path.join(TMP_DIR, "config.yaml.tmp")
    check_key = "proxies:"

    try:
        # Create both directories if they don't exist
        os.makedirs(MIHOMO_DIR, exist_ok=True)
        os.makedirs(TMP_DIR, exist_ok=True)
        
        print(f"[{service_name}] Downloading config... (User-Agent: {headers['User-Agent']})")

        response = requests.get(url, headers=headers, timeout=(10, 30), impersonate="firefox")
        response.raise_for_status()
        response.encoding = "utf-8"

        if check_key not in response.text:
             print(f"[{service_name}] Validation failed: Missing '{check_key}' - {time.strftime('%Y-%m-%d %H:%M:%S')}")
             return False

        with open(temp_path, "wb") as f:
            f.write(response.content)

        is_mihomo_valid = test_mihomo_config(temp_path)
        
        if is_mihomo_valid is False:
             print(f"[{service_name}] Invalid configuration detected. Discarding update.")
             os.remove(temp_path)
             return False

        need_restart = True
        if os.path.exists(save_path):
            with open(save_path, "rb") as f:
                if f.read() == response.content:
                    need_restart = False
                    print(f"[{service_name}] Config is identical to local, skipping restart.")

        # os.replace handles moving the file from \tmp\ to \clash\ and renaming it
        if need_restart or not os.path.exists(save_path):
             os.replace(temp_path, save_path)
             print(f"[{service_name}] Config updated successfully - {time.strftime('%Y-%m-%d %H:%M:%S')}")

             if need_restart:
                 if is_admin():
                     restart_service(service_name)
                 else:
                     print(f"[{service_name}] Skipping service restart (insufficient privileges).")
        else:
             # Delete from tmp folder if no restart/replace needed
             if os.path.exists(temp_path):
                 os.remove(temp_path)

        return True

    except requests.exceptions.RequestException as e:
        print(f"[{service_name}] Request Error: {e}")
    except Exception as e:
        print(f"[{service_name}] Unexpected error: {e}")
        # Clean up temp file on unexpected error
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return False


if __name__ == "__main__":
    print("Auto-update script started...")

    if not is_admin():
        print("[Warning] Script is not running as administrator!")
        print("Auto-download will work if directory permits, but **auto-restart will fail**.")
        print("Please right-click and 'Run as administrator'.")
        print("-" * 50)

    perform_update()
    last_update_time = time.time()

    try:
        while True:
            current_time = time.time()

            if current_time - last_update_time >= UPDATE_INTERVAL:
                perform_update()
                last_update_time = time.time()

            time.sleep(120)

    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service manually stopped.")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service stopped due to error: {e}")