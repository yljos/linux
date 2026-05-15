#!/usr/bin/env bash

# Install rsync if not present
if ! command -v rsync &> /dev/null; then
    apt-get update && apt-get install -y rsync
fi

rsync -r root/ /root/

if [[ -d "etc" ]]; then
    rsync -r etc/ /etc/
fi

# Fix file permissions
find /root/.ssh -type d -exec chmod 700 {} +
find /root/.ssh -type f -exec chmod 600 {} +