import os
import time
import subprocess
import ctypes
import shutil
from dotenv import load_dotenv
from curl_cffi import requests

# Configuration
UPDATE_INTERVAL = 3600  # 1 hour in seconds

# Clash Paths
CLASH_CONFIG_DIR = r"C:\clash"
CLASH_EXE = r"C:\Program Files\clash\mihomo-windows-amd64-v3.exe"

# Sing-box Paths
SINGBOX_CONFIG_DIR = r"C:\sing-box"
SINGBOX_EXE = r"C:\Program Files\sing-box\sing-box.exe"


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def restart_service(service_name):
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


def test_clash_config(tmp_config_path):
    print("Testing downloaded configuration using clash...")
    if not os.path.exists(CLASH_EXE):
        print(f"[Warning] Cannot find {CLASH_EXE}. Cannot validate.")
        return False

    try:
        tmp_dir = os.path.dirname(tmp_config_path)
        result = subprocess.run(
            [CLASH_EXE, "-t", "-d", tmp_dir, "-f", tmp_config_path],
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


def test_singbox_config(tmp_config_path):
    print("Testing downloaded configuration using sing-box...")
    if not os.path.exists(SINGBOX_EXE):
        print(f"[Warning] Cannot find {SINGBOX_EXE}. Cannot validate.")
        return False

    try:
        tmp_dir = os.path.dirname(tmp_config_path)
        result = subprocess.run(
            [SINGBOX_EXE, "check", "-D", tmp_dir, "-c", tmp_config_path],
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
    load_dotenv(override=True)
    url = os.getenv("URL")
    user_agent = os.getenv("USER_AGENT", "clash")
    headers = {"User-Agent": user_agent}

    if not url:
        print("Error: URL not found in .env, skipping this update.")
        return False

    if "sing-box" in user_agent.lower():
        service_name = "Sing-box"
        save_path = os.path.join(SINGBOX_CONFIG_DIR, "config.json")
        tmp_dir = os.path.join(SINGBOX_CONFIG_DIR, "tmp")
        temp_path = os.path.join(tmp_dir, "config.json")
        validator_func = test_singbox_config
    else:
        service_name = "clash"
        save_path = os.path.join(CLASH_CONFIG_DIR, "config.yaml")
        tmp_dir = os.path.join(CLASH_CONFIG_DIR, "tmp")
        temp_path = os.path.join(tmp_dir, "config.yaml")
        validator_func = test_clash_config

    try:
        os.makedirs(tmp_dir, exist_ok=True)
        print(f"[{service_name}] Downloading config... (User-Agent: {headers['User-Agent']})")

        response = requests.get(url, headers=headers, timeout=(10, 30), impersonate="firefox")
        response.raise_for_status()

        with open(temp_path, "wb") as f:
            f.write(response.content)

        if validator_func(temp_path):
            need_restart = True
            if os.path.exists(save_path):
                with open(save_path, "rb") as f:
                    if f.read() == response.content:
                        need_restart = False
                        print(f"[{service_name}] Config is identical to local, skipping restart.")

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
        if os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
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