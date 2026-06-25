from flask import Flask
from pathlib import Path
import threading

app = Flask(__name__)

# Constants
SHUTDOWN_FILE = Path("/data/www/shutdown")
AUTO_DELETE_DELAY_SEC = 62  # Units in seconds


def write_and_schedule(content):
    """Helper to write content to the file and schedule its deletion"""
    SHUTDOWN_FILE.write_text(content)
    # Delete the file after specified seconds
    threading.Timer(
        AUTO_DELETE_DELAY_SEC, lambda: SHUTDOWN_FILE.unlink(missing_ok=True)
    ).start()


@app.route("/auto")
def auto_create_and_delete():
    """Create file with 'AW' and schedule auto-deletion"""
    try:
        write_and_schedule("AW")
        return "All Devices will shutdown in 1 min"
    except Exception as e:
        return f"Operation failed: {e}", 500


@app.route("/w")
def write_w():
    """Create file with 'W' and schedule auto-deletion"""
    try:
        write_and_schedule("W")
        return "Windows will shutdown in 1 min"
    except Exception as e:
        return f"Operation failed: {e}", 500


@app.route("/a")
def write_a():
    """Create file with 'A' and schedule auto-deletion"""
    try:
        write_and_schedule("A")
        return "Arch Linux will shutdown in 1 min"
    except Exception as e:
        return f"Operation failed: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008)
