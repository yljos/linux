#!/usr/bin/bash

IP="10.0.0.15"
MAC="00:23:24:67:DF:14"
IFACE="enp0s31f6"
PASS="123"

# Execute the entire process in a background subshell to prevent blocking
(
    wakeonlan -i 10.0.0.255 "$MAC" >/dev/null 2>&1
    sleep 15
    xfreerdp3 /v:"$IP" /u:huai /p:"$PASS" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1
) &

