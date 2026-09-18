#!/usr/bin/bash

# Wrap all commands in a subshell and run it in the background
(
    MAC="00:23:24:67:DF:14"
    IP="10.0.0.15"

    if ! sudo arp-scan "$IP" 2>/dev/null | grep -qi "$MAC"; then
        wakeonlan -i 10.0.0.255 "$MAC" >/dev/null 2>&1

        count=0
        while ! sudo arp-scan "$IP" 2>/dev/null | grep -qi "$MAC"; do
            [ "$count" -ge 10 ] && exit 1
            sleep 3
            ((count++))
        done
    fi
    
    # Run xfreerdp detached from the subshell
    nohup xfreerdp /v:"$IP" /u:huai /p:"123" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
) >/dev/null 2>&1 &

# Detach the subshell from the terminal
disown