#!/usr/bin/env bash
if ! command -v rsync &> /dev/null; then
    apt-get update && apt-get install -y rsync
fi
rsync -r root/ /root/
rsync -r etc/ /etc/

find /root/.ssh -type d -exec chmod 700 {} +
find /root/.ssh -type f -exec chmod 600 {} +
