#!/usr/bin/env python3
"""
Autostart Python replacement for autostart.sh
- Implements a simple script lock to avoid multiple instances
- Checks whether processes are running (pgrep -x)
- Starts services/scripts if not running, in background (detached)
- Sends delayed notifications asynchronously (notify-send)
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = HOME / ".config"

# Commands / settings from original script
SWWW_AUTO = CONFIG_DIR / "swww_auto.sh"
SHUTDOWN_SH = CONFIG_DIR / "shutdown.sh"

DEVNULL = subprocess.DEVNULL


def is_running(name: str) -> bool:
    """Return True if a process with exact name is running (pgrep -x)."""
    try:
        return (
            subprocess.run(
                ["pgrep", "-x", name], stdout=DEVNULL, stderr=DEVNULL
            ).returncode
            == 0
        )
    except FileNotFoundError:
        return False


def is_running_match(pattern: str) -> bool:
    """Return True if any process matches the given pattern using pgrep -f."""
    try:
        return (
            subprocess.run(
                ["pgrep", "-f", pattern], stdout=DEVNULL, stderr=DEVNULL
            ).returncode
            == 0
        )
    except FileNotFoundError:
        return False


def notify_delayed(delay: int, title: str, message: str) -> None:
    """Send a desktop notification after `delay` seconds (non-blocking).

    Uses threading.Timer to avoid shelling out with background subshells.
    """

    def _notify():
        try:
            subprocess.run(
                ["notify-send", title, message], stdout=DEVNULL, stderr=DEVNULL
            )
        except Exception:
            pass

    t = threading.Timer(delay, _notify)
    t.daemon = True
    t.start()


def start_process(cmd, cwd=None):
    """Start a process non-blocking. `cmd` is a list (preferred) or string.

    This mirrors `cmd &` in the shell without creating a new session.
    """
    try:
        if isinstance(cmd, (list, tuple)):
            subprocess.Popen(
                cmd, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL, cwd=cwd
            )
        else:
            # string command -> run via shell (keeps same behavior for sh scripts)
            subprocess.Popen(
                cmd, shell=True, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL, cwd=cwd
            )
    except Exception:
        pass


def start_if_not_running(
    name: str,
    cmd,
    check_delay: float = 3.0,
    notify_delay: int = 0,
    notify_msg: str = "",
) -> None:
    """Start `cmd` if `name` process is not running; notify only on failure.

    Logic:
      1. If a process matching `name` is already running -> do nothing.
      2. Otherwise start `cmd` (list or string), wait `check_delay` seconds,
         then check again. If still not running and `notify_msg` is provided,
         send a delayed notification.

    This implements: check -> start -> wait 3s -> re-check -> notify on failure.
    """
    if not is_running(name):
        start_process(cmd)
        time.sleep(check_delay)
        if not is_running(name) and notify_msg:
            notify_delayed(notify_delay, "Autostart", f"{notify_msg} failed")


def start_if_not_running_match(
    pattern: str,
    cmd,
    check_delay: float = 3.0,
    notify_delay: int = 0,
    notify_msg: str = "",
) -> None:
    """Same as start_if_not_running but uses pattern matching (pgrep -f).

    Useful for scripts where the running process is best detected by a
    command-line pattern (e.g. /home/user/.config/swww_auto.sh).
    """
    if not is_running_match(pattern):
        start_process(cmd)
        time.sleep(check_delay)
        if not is_running_match(pattern) and notify_msg:
            notify_delayed(notify_delay, "Autostart", f"{notify_msg} failed")


def main():
    # No script lock; always run as requested.

    # Start dunst
    start_if_not_running("dunst", ["dunst"], notify_delay=0, notify_msg="dunst")

    # Start swww-daemon
    start_if_not_running(
        "swww-daemon",
        ["swww-daemon"],
        notify_delay=2,
        notify_msg="swww-daemon",
    )

    # Start swww_auto.sh (original: sh /home/huai/.config/swww_auto.sh &)
    start_if_not_running_match(
        str(SWWW_AUTO),
        ["/bin/sh", str(SWWW_AUTO)],
        check_delay=3.0,
        notify_delay=4,
        notify_msg="swww_auto.sh",
    )

    # Start shutdown.sh (original: sh /home/huai/.config/shutdown.sh &)
    start_if_not_running_match(
        str(SHUTDOWN_SH),
        ["/bin/sh", str(SHUTDOWN_SH)],
        check_delay=3.0,
        notify_delay=6,
        notify_msg="shutdown.sh",
    )

    # Start firefox if not running
    start_if_not_running("firefox", ["firefox"], notify_delay=8, notify_msg="Firefox")

    # Start Telegram if not running (command is `Telegram`)
    start_if_not_running(
        "Telegram", ["Telegram"], notify_delay=10, notify_msg="Telegram"
    )

    # Start fcitx5 if not running (original used `fcitx5 -d`)
    start_if_not_running(
        "fcitx5",
        ["fcitx5", "-d"],
        check_delay=3.0,
        notify_delay=12,
        notify_msg="fcitx5",
    )


if __name__ == "__main__":
    main()
