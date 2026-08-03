import os
import time
import subprocess
import ctypes
import json
from dotenv import load_dotenv
from curl_cffi import requests

# Configuration
UPDATE_INTERVAL = 3600  # 1 hour in seconds

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

def perform_update():
    """Execute the update process based on User-Agent"""
    load_dotenv(override=True)
    url = os.getenv("URL")
    
    # Default to clash_pc if USER_AGENT is not set
    user_agent = os.getenv("USER_AGENT", "clash_pc")
    headers = {"User-Agent": user_agent}

    if not url:
        print("Error: URL not found in .env, skipping this update.")
        return False

    # Mutually exclusive logic based on USER_AGENT
    if "sing-box" in user_agent.lower():
        service_name = "Sing-box"
        save_path = r"c:\sing-box\config.json"
        check_key = "outbounds"
        is_json = True
    else:
        service_name = "Mihomo"
        save_path = r"c:\mihomo\config.yaml"
        check_key = "proxies:"
        is_json = False

    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        print(f"[{service_name}] Downloading config... (User-Agent: {headers['User-Agent']})")

        # Bypass Bot Fight Mode by impersonating Chrome
        response = requests.get(
            url, headers=headers, timeout=(10, 30), impersonate="firefox"
        )
        response.raise_for_status()
        response.encoding = "utf-8"

        is_valid = False
        if is_json:
            try:
                config_data = response.json()
                if check_key in config_data:
                    is_valid = True
            except json.JSONDecodeError:
                pass
        else:
            if check_key in response.text:
                is_valid = True

        if is_valid:
            # Atomic write
            temp_path = save_path + ".tmp"
            with open(temp_path, "wb") as f:
                f.write(response.content)
            os.replace(temp_path, save_path)

            print(f"[{service_name}] Config updated successfully - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if is_admin():
                restart_service(service_name)
            else:
                print(f"[{service_name}] Skipping service restart (insufficient privileges).")
            return True
        else:
            print(f"[{service_name}] Validation failed: Missing '{check_key}' - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[{service_name}] Request Error: {e}")
    except Exception as e:
        print(f"[{service_name}] Unexpected error: {e}")
        # Clean up temp file on unexpected error if it exists
        temp_path = save_path + ".tmp"
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
        print("Auto-download will work, but **auto-restart will fail**.")
        print("Please right-click and 'Run as administrator'.")
        print("-" * 50)

    # Execute update immediately upon script startup
    perform_update()
    last_update_time = time.time()

    try:
        while True:
            current_time = time.time()

            if current_time - last_update_time >= UPDATE_INTERVAL:
                perform_update()
                last_update_time = time.time()

            # Sleep 120 seconds to prevent high CPU usage and allow manual interrupts
            time.sleep(120)

    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service manually stopped.")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service stopped due to error: {e}")