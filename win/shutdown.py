import time
import subprocess
import requests
import datetime

# Core configuration
URL = "http://10.0.0.21:80/shutdown"
WAIT_SECONDS = 1 * 60  # Check interval: 1 minutes


def main():
    print(f"[{datetime.datetime.now()}] Service started.")
    
    # Initial delay before entering the loop
    time.sleep(WAIT_SECONDS)

    while True:
        try:
            # Log every check attempt
            print(f"[{datetime.datetime.now()}] Checking URL: {URL}")
            
            # Try to fetch remote signal
            response = requests.get(URL, timeout=5)

            # Trigger shutdown if successful and content contains "W"
            if response.status_code == 200 and "W" in response.text:
                print(f"[{datetime.datetime.now()}] Signal received. Shutting down...")
                subprocess.run(["shutdown", "/s", "/f", "/t", "0"], check=True)
                break  # Exit loop after successful shutdown command

        except Exception as e:
            # Log the error
            print(f"[{datetime.datetime.now()}] Error: {e}")

        # Wait before the next check
        time.sleep(WAIT_SECONDS)


if __name__ == "__main__":
    main()