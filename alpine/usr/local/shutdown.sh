#!/bin/sh

SHUTDOWN_FILE="http://10.0.0.21/shutdown"
INTERVAL=60 # Loop interval in seconds

# Initial delay before entering the loop
sleep "$INTERVAL"

while true; do
    # Fetch content; -f fails silently on HTTP errors (e.g., 404/500)
    CONTENT=$(curl -fs --connect-timeout 1 --max-time 2 "$SHUTDOWN_FILE")

    # Check for trigger character
    case "$CONTENT" in
        *A*)
            sleep 60
            poweroff
            exit 0
            ;;
    esac

    # Wait before next check
    sleep "$INTERVAL"
done