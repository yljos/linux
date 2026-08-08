#!/usr/bin/bash

# Define variables
MAC="00:23:24:67:DF:14"
IP="10.0.0.15"

# Check if the host is online using arp-scan, wake and wait if offline
if ! sudo arp-scan "$IP" | grep -qi "$MAC"; then
	wakeonlan -i 10.0.0.255 "$MAC" >/dev/null 2>&1

	# Wait until the host is up, max 10 loops
	count=0
	while ! sudo arp-scan "$IP" | grep -qi "$MAC"; do
		[ "$count" -ge 10 ] && exit 1
		sleep 3
		((count++))
	done
fi
xfreerdp /v:"$IP" /u:huai /p:"123" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
