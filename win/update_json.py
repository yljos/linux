import os
import time
import subprocess
import ctypes
import json
from dotenv import load_dotenv
from curl_cffi import requests

# Configuration
SERVICE_NAME = "Sing-box"
save_path = r"c:\sing-box\config.json"
UPDATE_INTERVAL = 3600  # 1 hour in seconds


def is_admin():
    """Check for administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def restart_service():
    """Restart the Sing-box service"""
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
    user_agent = os.getenv("USER_AGENT", "sing-box_pc")
    headers = {"User-Agent": user_agent}

    if not url:
        print("Error: URL not found in .env, skipping this update.")
        return False

    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        print(f"Downloading config... (User-Agent: {headers['User-Agent']})")

        # Bypass Bot Fight Mode by impersonating Chrome
        response = requests.get(
            url, headers=headers, timeout=(10, 30), impersonate="chrome"
        )
        response.raise_for_status()
        response.encoding = "utf-8"

        try:
            config_data = response.json()

            if "outbounds" in config_data:
                # Atomic write: write to temp file first, then replace
                temp_path = save_path + ".tmp"
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                os.replace(temp_path, save_path)

                print(
                    f"Config updated successfully - {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                if is_admin():
                    restart_service()
                else:
                    print("Skipping service restart (insufficient privileges).")
                return True
            else:
                print(
                    f"Validation failed: JSON missing 'outbounds' - {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                return False

        except json.JSONDecodeError:
            print(
                f"Validation failed: Invalid JSON - {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return False

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
    except requests.exceptions.ConnectionError:
        print("Connection failed.")
    except requests.exceptions.Timeout:
        print("Request timeout.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Clean up temp file on unexpected error if it exists
        temp_path = save_path + ".tmp"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return False


if __name__ == "__main__":
    print(f"Auto-update script started (Target: {SERVICE_NAME})...")

    if not is_admin():
        print("[Warning] Script is not running as administrator!")
        print("Auto-download will work, but **auto-restart will fail**.")
        print("Please right-click and 'Run as administrator'.")
        print("-" * 50)

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

            # Sleep 120 seconds to prevent high CPU usage and allow manual interrupts
            time.sleep(120)

    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service manually stopped.")
    except Exception as e:
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service stopped due to error: {e}"
        )
