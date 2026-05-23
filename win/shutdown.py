import time
import subprocess
import requests

# Core configuration
URL = "http://10.0.0.21:80/shutdown"
WAIT_SECONDS = 1 * 60  # Check interval: 1 minutes


def main():
    # Initial delay before entering the loop
    time.sleep(WAIT_SECONDS)

    while True:
        try:
            # Try to fetch remote signal
            response = requests.get(URL, timeout=5)

            # Trigger shutdown if successful and content is "1"
            if response.status_code == 200 and response.text.strip() == "1":
                subprocess.run(["shutdown", "/s", "/f", "/t", "0"], check=True)
                break  # Exit loop after successful shutdown command

        except Exception:
            # Silently catch all exceptions (timeout, network down, etc.)
            pass

        # Wait before the next check
        time.sleep(WAIT_SECONDS)


if __name__ == "__main__":
    main()
