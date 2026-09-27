import os
import time
import subprocess
import ctypes
from dotenv import load_dotenv
from curl_cffi import requests

# Configuration
UPDATE_INTERVAL = 3600  # 1 hour in seconds
CLASH_DIR = r"C:\clash"
CLASH_EXE = r"C:\Program Files\clash\mihomo-windows-amd64-v3.exe"
SINGBOX_DIR = r"C:\sing-box"
SINGBOX_EXE = os.path.join(SINGBOX_DIR, "sing-box.exe")


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


def test_clash_config(config_path):
    """Test the validity of the clash configuration file using clash itself"""
    print("Testing downloaded configuration using clash...")
    if not os.path.exists(CLASH_EXE):
        print(f"[Warning] Cannot find {CLASH_EXE}. Cannot validate.")
        return False

    try:
        # Run clash test: -d for runtime directory, -f for config file
        result = subprocess.run(
            [CLASH_EXE, "-t", "-d", CLASH_DIR, "-f", config_path],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        output_lower = result.stdout.lower()
        if result.returncode == 0 and "test is successful" in output_lower:
            print("[Success] Configuration is valid.")
            return True
        else:
            print(f"[Error] Configuration validation failed. Output:\n{result.stdout}\n{result.stderr}")
            return False
    except Exception as e:
        print(f"[Error] Failed to execute clash test: {e}")
        return False


def test_singbox_config(config_path):
    """Test the validity of the sing-box configuration file using sing-box itself"""
    print("Testing downloaded configuration using sing-box...")
    if not os.path.exists(SINGBOX_EXE):
        print(f"[Warning] Cannot find {SINGBOX_EXE}. Cannot validate.")
        return False

    try:
        # Run sing-box test: check -c for config file
        result = subprocess.run(
            [SINGBOX_EXE, "check", "-c", config_path],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode == 0:
            print("[Success] Configuration is valid.")
            return True
        else:
            print(f"[Error] Configuration validation failed. Output:\n{result.stderr or result.stdout}")
            return False
    except Exception as e:
        print(f"[Error] Failed to execute sing-box test: {e}")
        return False


def perform_update():
    """Execute the update process based on User-Agent"""
    load_dotenv(override=True)
    url = os.getenv("URL")
    user_agent = os.getenv("USER_AGENT", "clash")
    headers = {"User-Agent": user_agent}

    if not url:
        print("Error: URL not found in .env, skipping this update.")
        return False

    if "sing-box" in user_agent.lower():
        service_name = "sing-box"
        save_path = os.path.join(SINGBOX_DIR, "config.json")
        validator_func = test_singbox_config
    else:
        service_name = "clash"
        save_path = os.path.join(CLASH_DIR, "config.yaml")
        validator_func = test_clash_config

    tmp_dir = os.path.join(os.path.dirname(save_path), "tmp")
    temp_path = os.path.join(tmp_dir, os.path.basename(save_path))

    try:
        os.makedirs(tmp_dir, exist_ok=True)
        print(f"[{service_name}] Downloading config... (User-Agent: {headers['User-Agent']})")

        response = requests.get(url, headers=headers, timeout=(10, 30), impersonate="firefox")
        response.raise_for_status()

        # Write to temporary file in tmp folder
        with open(temp_path, "wb") as f:
            f.write(response.content)

        # Validate configuration
        if validator_func(temp_path):
            need_restart = True
            if os.path.exists(save_path):
                with open(save_path, "rb") as f:
                    if f.read() == response.content:
                        need_restart = False
                        print(f"[{service_name}] Config is identical to local, skipping restart.")

            # Atomic replace
            os.replace(temp_path, save_path)
            print(f"[{service_name}] Config updated successfully - {time.strftime('%Y-%m-%d %H:%M:%S')}")

            if need_restart:
                if is_admin():
                    restart_service(service_name)
                else:
                    print(f"[{service_name}] Skipping service restart (insufficient privileges).")
            return True
        else:
            print(f"[{service_name}] Update aborted due to invalid configuration - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
    except requests.exceptions.RequestException as e:
        print(f"[{service_name}] Request Error: {e}")
    except Exception as e:
        print(f"[{service_name}] Unexpected error: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return False


if __name__ == "__main__":
    print("Auto-update script started...")
    if not is_admin():
        print("[Warning] Script is not running as administrator!\nAuto-download will work, but **auto-restart will fail**.\nPlease right-click and 'Run as administrator'.\n" + "-" * 50)

    perform_update()
    last_update_time = time.time()

    try:
        while True:
            if time.time() - last_update_time >= UPDATE_INTERVAL:
                perform_update()
                last_update_time = time.time()
            time.sleep(120)
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service manually stopped.")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Service stopped due to error: {e}")