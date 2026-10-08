# /// script
# dependencies = [
#   "requests",
# ]
# ///

import datetime
import subprocess
import time
import requests

# Core configuration
URL = "http://10.0.0.21:80/shutdown"
WAIT_SECONDS = 1 * 60  # Check interval: 1 minute


def log(msg: str):
    # Standard timestamped logging
    now = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    print(f"[{now}] {msg}")


def main():
    log("Service started.")
    time.sleep(WAIT_SECONDS)

    # Reuse TCP connection session
    with requests.Session() as session:
        while True:
            try:
                log(f"Checking URL: {URL}")
                response = session.get(URL, timeout=5)

                if response.status_code == 200 and "W" in response.text:
                    log("Signal received. Shutting down...")
                    subprocess.run(["shutdown", "/s", "/f", "/t", "0"], check=True)
                    break

            except requests.RequestException as e:
                # Log network/HTTP errors only
                log(f"Request error: {e}")

            time.sleep(WAIT_SECONDS)


if __name__ == "__main__":
    main()