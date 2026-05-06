from flask import Flask
from pathlib import Path
import threading
from datetime import datetime

app = Flask(__name__)

# Constants
SHUTDOWN_FILE = Path("/data/www/shutdown")
AUTO_DELETE_DELAY_MIN = 2


def delayed_delete(file_path: Path, delay_min: int):
    """Delete the file after specified minutes"""
    threading.Timer(delay_min * 60, lambda: file_path.unlink(missing_ok=True)).start()


def get_time() -> str:
    """Return current formatted time string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/auto")
def auto_create_and_delete():
    """Create file and schedule auto-deletion"""
    t = get_time()
    try:
        SHUTDOWN_FILE.write_text("1")
        delayed_delete(SHUTDOWN_FILE, AUTO_DELETE_DELAY_MIN)
        return f"[{t}] Created {SHUTDOWN_FILE}, auto-deleting in {AUTO_DELETE_DELAY_MIN} mins"
    except Exception as e:
        return f"[{t}] Operation failed: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008)
