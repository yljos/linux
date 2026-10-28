#!/bin/sh

SHUTDOWN_FILE="http://www.lan/a"
INTERVAL=60 # Loop interval in seconds

# Initial delay before entering the loop
sleep "$INTERVAL"

while true; do
    # Fetch HTTP status code only
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 --max-time 2 "$SHUTDOWN_FILE")

    # 200: file exists (trigger shutdown)
    # 204: file absent (continue polling)
    if [ "$STATUS" = "200" ]; then
        sleep 60
        poweroff
        exit 0
    fi

    # Wait before next check
    sleep "$INTERVAL"
done