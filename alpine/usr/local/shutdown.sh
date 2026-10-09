#!/bin/sh

SHUTDOWN_FILE="http://10.0.0.21/shutdown"
INTERVAL=60 # Loop interval in seconds

# Initial delay before entering the loop
sleep "$INTERVAL"

while true; do
	# Fetch remote file content with optimized timeout
	CONTENT=$(curl -s --connect-timeout 1 --max-time 2 "$SHUTDOWN_FILE")

	# Empty content or curl failed -> wait for next round
	if [ -z "$CONTENT" ]; then
		sleep "$INTERVAL"
		continue
	fi

	# If content contains 'A', execute shutdown
	case "$CONTENT" in
		*A*)
			sleep 60
			poweroff # Alpine OpenRC/BusyBox shutdown command
			exit 0
			;;
	esac

	# Wait before next check
	sleep "$INTERVAL"
done