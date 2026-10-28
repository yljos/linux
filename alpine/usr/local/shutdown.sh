#!/bin/sh

SHUTDOWN_FILE="http://www.lan/a"
INTERVAL=60 # Loop interval in seconds

# Initial delay before entering the loop
sleep "$INTERVAL"

while true; do
    # Check if target file exists; -f returns non-zero on HTTP errors (e.g., 404/500)
    if curl -fs --connect-timeout 1 --max-time 2 "$SHUTDOWN_FILE" > /dev/null 2>&1; then
        sleep 60
        poweroff
        exit 0
    fi

    # Wait before next check
    sleep "$INTERVAL"
done