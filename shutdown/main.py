from flask import Flask
from pathlib import Path
import threading

app = Flask(__name__)

# Constants
SHUTDOWN_FILE = Path("/data/www/shutdown")
AUTO_DELETE_DELAY_SEC = 62  # Units in seconds


@app.route("/auto")
def auto_create_and_delete():
    """Create file and schedule auto-deletion"""
    try:
        SHUTDOWN_FILE.write_text("1")
        # Delete the file after specified seconds
        threading.Timer(
            AUTO_DELETE_DELAY_SEC, lambda: SHUTDOWN_FILE.unlink(missing_ok=True)
        ).start()
        return "Command executed"
    except Exception as e:
        return f"Operation failed: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008)
