#!/usr/bin/bash
IP="10.0.0.15"
PASS="123"
# Execute the entire process in a background subshell to prevent blocking
xfreerdp3 /v:"$IP" /u:huai /p:"$PASS" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
