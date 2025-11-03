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
    name: str, cmd, notify_delay: int = 0, notify_msg: str = ""
) -> None:
    """Start `cmd` if `name` process is not running, then optionally notify after delay."""
    if not is_running(name):
        start_process(cmd)
        time.sleep(0.5)
        if is_running(name) and notify_msg:
            notify_delayed(notify_delay, "Autostart", notify_msg)


def main():
    # No script lock; always run as requested.

    # Start dunst
    start_if_not_running(
        "dunst", ["dunst"], notify_delay=0, notify_msg="启动 dunst 通知守护进程"
    )

    # Start swww-daemon
    start_if_not_running(
        "swww-daemon",
        ["swww-daemon"],
        notify_delay=2,
        notify_msg="启动 swww-daemon 壁纸守护进程",
    )

    # Start swww_auto.sh (original: sh /home/huai/.config/swww_auto.sh &)
    start_process(["/bin/sh", str(SWWW_AUTO)])
    notify_delayed(4, "Autostart", "启动 swww_auto.sh 壁纸脚本")

    # Start shutdown.sh (original: sh /home/huai/.config/shutdown.sh &)
    start_process(["/bin/sh", str(SHUTDOWN_SH)])
    notify_delayed(6, "Autostart", "启动 shutdown.sh 关机脚本")

    # Start firefox if not running
    start_if_not_running(
        "firefox", ["firefox"], notify_delay=8, notify_msg="启动 Firefox 浏览器"
    )

    # Start Telegram if not running
    start_if_not_running(
        "Telegram", ["Telegram"], notify_delay=10, notify_msg="启动 Telegram 即时通讯"
    )

    # Start fcitx5 if not running (original used `fcitx5 -d`)
    if not is_running("fcitx5"):
        start_process(["fcitx5", "-d"])
        time.sleep(0.5)
        if is_running("fcitx5"):
            notify_delayed(12, "Autostart", "启动 fcitx5 输入法")


if __name__ == "__main__":
    main()
