#!/bin/sh

# Sync root directory
rsync -r root/ /root/

# Sync etc directory if it exists
if [ -d "etc" ]; then
    rsync -r etc/ /etc/
fi

# Fix file permissions
if [ -d "/root/.ssh" ]; then
    find /root/.ssh -type d -exec chmod 700 {} +
    find /root/.ssh -type f -exec chmod 600 {} +
fi