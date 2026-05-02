#!/usr/bin/env bash
git config --global core.editor "vim"
git config --global user.signingkey CABB8B2144528A69
git config --global commit.gpgsign true
git config --global user.name "bite-os"
git config --global user.email "bite-os@biteos.org"

curl -s "http://10.0.0.21/key/20260429_pub.asc" | gpg --import >/dev/null 2>&1

systemctl --user daemon-reload && systemctl --user enable --now pipewire wireplumber shutdown >/dev/null 2>&1
# [ -f /etc/krb5.conf ] && sudo sed -i 's/^/#/' /etc/krb5.conf
sudo tee /etc/krb5.conf </dev/null
