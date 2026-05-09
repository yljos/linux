#!/usr/bin/env bash

rsync -r huai/ /home/huai/

if [[ -d "etc" ]]; then
	rsync -r etc/ /etc/
fi
# Fix directory permissions
chown huai:huai -R /home/huai/

# Fix file permissions
find /home/huai/.ssh /home/huai/.gnupg -type d -exec chmod 700 {} +
find /home/huai/.ssh /home/huai/.gnupg -type f -exec chmod 600 {} +
