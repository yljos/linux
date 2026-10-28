from flask import Flask
from pathlib import Path
import sched
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

# Event-driven scheduler setup
scheduler = sched.scheduler(time.time, time.sleep)
scheduler_cv = threading.Condition()
active_events = {}


def scheduler_worker():
    """Event-driven scheduler loop with zero-busy-wait"""
    while True:
        with scheduler_cv:
            # Wait when no events exist
            while scheduler.empty():
                scheduler_cv.wait()

            # Wait until the next earliest event is ready to run
            delay = scheduler.queue[0].time - time.time()
            if delay > 0:
                scheduler_cv.wait(timeout=delay)

            # Re-check and run expired events
            if not scheduler.empty() and scheduler.queue[0].time <= time.time():
                scheduler.run(blocking=False)


def delete_file(file_path: Path):
    """Callback to remove expired file and clear tracking handle"""
    file_path.unlink(missing_ok=True)
    with scheduler_cv:
        active_events.pop(file_path, None)


def schedule_trigger(file_path: Path):
    """Touch empty file and register/refresh cancellation event"""
    file_path.touch(exist_ok=True)

    with scheduler_cv:
        # Cancel previous scheduled deletion if duplicate trigger arrives
        prev_event = active_events.get(file_path)
        if prev_event:
            try:
                scheduler.cancel(prev_event)
            except ValueError:
                pass

        # Schedule new deletion task
        new_event = scheduler.enter(DELETE_DELAY_SEC, 1, delete_file, (file_path,))
        active_events[file_path] = new_event
        scheduler_cv.notify()


def init_cleanup():
    """Check leftovers on startup and schedule recovery deletions"""
    now = time.time()
    for target in (FILE_W, FILE_A):
        try:
            mtime = target.stat().st_mtime
            remaining = DELETE_DELAY_SEC - (now - mtime)
            if remaining <= 0:
                target.unlink(missing_ok=True)
            else:
                with scheduler_cv:
                    event = scheduler.enter(remaining, 1, delete_file, (target,))
                    active_events[target] = event
        except FileNotFoundError:
            continue


@app.route("/w")
def create_w():
    try:
        schedule_trigger(FILE_W)
        return "Windows shutdown scheduled"
    except Exception as e:
        return f"Operation failed: {e}", 500


@app.route("/a")
def create_a():
    try:
        schedule_trigger(FILE_A)
        return "Arch Linux shutdown scheduled"
    except Exception as e:
        return f"Operation failed: {e}", 500


@app.route("/auto")
def create_auto():
    try:
        schedule_trigger(FILE_W)
        schedule_trigger(FILE_A)
        return "All devices shutdown scheduled"
    except Exception as e:
        return f"Operation failed: {e}", 500


if __name__ == "__main__":
    init_cleanup()
    threading.Thread(target=scheduler_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=5008)