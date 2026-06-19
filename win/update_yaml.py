import os
import time
import subprocess
import ctypes
from dotenv import load_dotenv
from curl_cffi import requests

# Configuration
SERVICE_NAME = "Mihomo"
save_path = r"c:\mihomo\config.yaml"
UPDATE_INTERVAL = 3600  # 1 hour in seconds


def is_admin():
    """Check for administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def restart_service():
    """Restart the Mihomo service"""
    print(f"Attempting to restart service: {SERVICE_NAME} ...")
    try:
        subprocess.run(["net", "stop", SERVICE_NAME], check=False, shell=True)
        time.sleep(2)
        subprocess.run(["net", "start", SERVICE_NAME], check=True, shell=True)
        print(f"[Success] Service {SERVICE_NAME} restarted.")
    except subprocess.CalledProcessError as e:
        print(f"[Failed] Service startup failed: {e}")
    except Exception as e:
        print(f"Unknown error during service restart: {e}")


def perform_update():
    """Execute the update process"""
    load_dotenv(override=True)
    url = os.getenv("URL")
    user_agent = os.getenv("USER_AGENT", "clash_pc")
    headers = {"User-Agent": user_agent}

    if not url:
        print("Error: URL not found in .env, skipping this update.")
        return False

    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        print(f"Downloading config... (User-Agent: {headers['User-Agent']})")

        # Bypass Bot Fight Mode by impersonating Chrome
        response = requests.get(url, headers=headers, timeout=(10, 30), impersonate="chrome")
        response.raise_for_status()
        response.encoding = "utf-8"

        if "proxies:" in response.text:
            with open(save_path, "wb") as f:
                f.write(response.content)

            print(f"Config updated successfully - {time.strftime('%Y-%m-%d %H:%M:%S')}")

            if is_admin():
                restart_service()
            return True
        else:
            print(f"Validation failed: No 'proxies:' found. - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            return False

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
    except requests.exceptions.ConnectionError:
        print("Connection failed.")
    except requests.exceptions.Timeout:
        print("Request timeout.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    return False


if __name__ == "__main__":
    print(f"Auto-update script started (Target: {SERVICE_NAME})...")

    # Execute update immediately upon script startup
    print("Executing initial update on startup...")
    perform_update()
    
    # Initialize the timestamp after the first run
    last_update_time = time.time()

    try:
        while True:
            current_time = time.time()
            
            # Check if UPDATE_INTERVAL has passed since the last update
            if current_time - last_update_time >= UPDATE_INTERVAL:
                perform_update()
                # Reset timestamp regardless of success to avoid spamming the server
                last_update_time = time.time() 

            # Sleep 10 seconds to prevent high CPU usage and allow manual interrupts
            time.sleep(10)

    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service manually stopped.")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service stopped due to error: {e}")