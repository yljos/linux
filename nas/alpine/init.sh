#!/bin/sh

# Check and install rsync if not found
if ! command -v rsync >/dev/null 2>&1; then
    apk add --no-cache rsync
fi

# Synchronize root home files
rsync -r root/ /root/

# Synchronize system configuration if present
if [ -d "etc" ]; then
    rsync -r etc/ /etc/
fi

# Fix ssh directory and file permissions if directory exists
if [ -d "/root/.ssh" ]; then
    find /root/.ssh -type d -exec chmod 700 {} +
    find /root/.ssh -type f -exec chmod 600 {} +
fi