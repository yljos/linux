#!/usr/bin/env bash

rsync -r huai/ /home/huai/

if [[ -d "etc" ]]; then
	rsync -r etc/ /etc/
fi
# Fix directory permissions
chown huai:huai -R /home/huai/

# Fix file permissions
find /home/huai/.ssh  -type d -exec chmod 700 {} +
find /home/huai/.ssh  -type f -exec chmod 600 {} +

