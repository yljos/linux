#!/usr/bin/env bash

rsync -r huai/ /home/huai/

if [[ -d "etc" ]]; then
	rsync -r etc/ /etc/
fi
if [[ -d "usr" ]]; then
	rsync -r usr/ /usr/
fi

chown huai:huai -R /home/huai/

find /home/huai/.ssh /home/huai/.gnupg -type d -exec chmod 700 {} + 2>/dev/null
find /home/huai/.ssh /home/huai/.gnupg -type f -exec chmod 600 {} + 2>/dev/null

systemctl daemon-reload
systemctl enable --now shutdown >/dev/null 2>&1
systemctl enable --now pcscd.socket

tee /etc/krb5.conf </dev/null

echo "Arch Linux initialization complete."
