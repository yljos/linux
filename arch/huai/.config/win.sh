#!/usr/bin/bash

# Define password file path
PASS_FILE="$HOME/m"

# Exit silently if password file does not exist
[ ! -f "$PASS_FILE" ] && exit 1

# Read password from file
read -r PASS < "$PASS_FILE"

IP="10.0.0.15"

# Prioritize Wayland, fallback to X11 directly
if [ -n "$WAYLAND_DISPLAY" ]; then
    wlfreerdp3 /v:"$IP" /u:huai /p:"$PASS" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
else
    xfreerdp3 /v:"$IP" /u:huai /p:"$PASS" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
fi