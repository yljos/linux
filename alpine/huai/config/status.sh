#!/bin/sh

while true; do
	# Update root window name with current time
	xsetroot -name "$(date '+%a %Y-%m-%d %H:%M')" 2>/dev/null

	# Sleep until the next full minute
	sleep $((60 - $(date +%S)))
done