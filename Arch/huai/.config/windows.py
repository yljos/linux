#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import shutil

CONFIG_GPG = os.path.expanduser("~/.config/mima.gpg")
TARGET_IP = "192.168.31.15"
MAC_ADDRESS = "00:23:24:67:DF:14"
INTERFACE = "enp0s31f6"
MAX_TRIES = 15

# 通知和音效
NOTIFY_CMD = "notify-send"
PLAY_CMD = "play"
DUNST_PATH = os.path.expanduser("~/.config/dunst/")

# 依赖列表
DEPENDENCIES = ["arping", "wakeonlan", "notify-send", "gpg", "play", "sdl-freerdp3"]


def notify(title, msg, sound=None):
    subprocess.run([NOTIFY_CMD, title, msg])
    if sound:
        subprocess.run(
            [PLAY_CMD, os.path.join(DUNST_PATH, sound)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def check_dependencies():
    for cmd in DEPENDENCIES:
        if shutil.which(cmd) is None:
            print(f"Missing dependency: {cmd}", file=sys.stderr)
            sys.exit(1)


def decrypt_password():
    if not os.path.isfile(CONFIG_GPG):
        notify("Error", f"Missing config: {CONFIG_GPG}")
        sys.exit(1)
    try:
        result = subprocess.run(
            ["gpg", "-d", CONFIG_GPG], capture_output=True, text=True, check=True
        )
        password = result.stdout.strip()
        return password
    except subprocess.CalledProcessError:
        notify("Error", f"Failed to decrypt: {CONFIG_GPG}")
        sys.exit(1)


def wake_host():
    notify("Waking", "Sending WOL packet...", "wol.mp3")
    result = subprocess.run(
        ["wakeonlan", "-i", "192.168.31.255", MAC_ADDRESS],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        notify("Wake failed", "Check network", "error.mp3")
        sys.exit(1)
    notify("Waiting", "Checking...", "starting.mp3")


def wait_online():
    for i in range(1, MAX_TRIES + 1):
        result = subprocess.run(
            ["sudo", "arping", "-c", "1", "-w", "1", "-q", "-I", INTERFACE, TARGET_IP],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            notify("Online", "Starting connection", "system_online.mp3")
            return True
        time.sleep(1)
    notify("Timeout", "Host did not respond", "error.mp3")
    sys.exit(1)


def connect_to_host(password):
    notify("Connecting", "Starting RDP...", "connecting.mp3")
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "wayland"
    subprocess.Popen(
        [
            "sdl-freerdp3",
            f"/v:{TARGET_IP}",
            "/u:huai",
            f"/p:{password}",
            "/cert:ignore",
            "/sound",
            "/w:1916",
            "/h:1056",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    # check_dependencies()
    password = decrypt_password()
    result = subprocess.run(
        ["sudo", "arping", "-c", "1", "-w", "1", "-q", "-I", INTERFACE, TARGET_IP],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 0:
        notify("Online", "Connecting...", "system_online.mp3")
        connect_to_host(password)
    else:
        wake_host()
        if wait_online():
            connect_to_host(password)


if __name__ == "__main__":
    main()
