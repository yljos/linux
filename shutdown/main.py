from flask import Flask
from pathlib import Path
import threading
import time

app = Flask(__name__)

# Constants
BASE_DIR = Path("/data/www")
FILE_W = BASE_DIR / "w"
FILE_A = BASE_DIR / "a"
DELETE_DELAY_SEC = 60

# Ensure target directory exists
BASE_DIR.mkdir(parents=True, exist_ok=True)


def file_cleanup_worker():
    """Scan files and remove them if age exceeds the threshold"""
    targets = (FILE_W, FILE_A)
    while True:
        now = time.time()
        for target in targets:
            try:
                # Compare current time with inode modification time
                if now - target.stat().st_mtime >= DELETE_DELAY_SEC:
                    target.unlink(missing_ok=True)
            except FileNotFoundError:
                continue
        time.sleep(1)


def touch_file(file_path: Path):
    """Create empty file or update mtime if it already exists"""
    file_path.touch(exist_ok=True)


@app.route("/w")
def create_w():
    try:
        touch_file(FILE_W)
        return "Windows shutdown scheduled"
    except Exception as e:
        return f"Operation failed: {e}", 500


@app.route("/a")
def create_a():
    try:
        touch_file(FILE_A)
        return "Arch Linux shutdown scheduled"
    except Exception as e:
        return f"Operation failed: {e}", 500


@app.route("/auto")
def create_auto():
    try:
        touch_file(FILE_W)
        touch_file(FILE_A)
        return "All devices shutdown scheduled"
    except Exception as e:
        return f"Operation failed: {e}", 500


if __name__ == "__main__":
    # Start background cleanup thread
    threading.Thread(target=file_cleanup_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5008)