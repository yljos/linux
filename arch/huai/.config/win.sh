#!/usr/bin/bash

# Require password as the first argument
if [ -z "$1" ]; then
    echo "Usage: win <password>"
    exit 1
fi

IP="10.0.0.15"
PASS="$1"

# Execute the entire process in a background subshell to prevent blocking
xfreerdp3 /v:"$IP" /u:huai /p:"$PASS" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
