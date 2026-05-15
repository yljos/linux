#!/usr/bin/bash

# Load script lock library
source "$HOME/.config/script_lock.sh"
# Check script lock
acquire_script_lock || exit 0

SHUTDOWN_FILE="http://10.0.0.21/shutdown"
INTERVAL=60 # Polling interval in seconds

while true; do
	# Fetch remote file content, optimized timeout for LAN
	CONTENT=$(curl -s --connect-timeout 1 --max-time 2 "$SHUTDOWN_FILE")

	# File not found or curl failed -> wait for next round
	if [ -z "$CONTENT" ]; then
		sleep "$INTERVAL"
		continue
	fi

	# If content is 1 -> poweroff
	if [ "$CONTENT" = "1" ]; then
		notify-send -u critical "Shutdown signal detected" "System will shut down in 60 seconds"
		sleep 60

		sudo poweroff # Comment out for testing
		exit 0
	fi

	# Wait fixed interval before next check
	sleep "$INTERVAL"
done
