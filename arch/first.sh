#!/usr/bin/env bash
git config --global core.editor "vim"
git config --global user.signingkey B5E5D5D7F179195B
git config --global commit.gpgsign true
git config --global user.name "bite-os"
git config --global user.email "bite-os@biteos.org"

curl -L "http://10.0.0.21/key/id_ed25519_lan.gpg" -o /home/huai/.ssh/id_ed25519_lan.gpg >/dev/null 2>&1
curl -L "http://10.0.0.21/key/id_ed25519_cloud.gpg" -o /home/huai/.ssh/id_ed25519_cloud.gpg >/dev/null 2>&1
curl -L "http://10.0.0.21/key/id_ed25519_lan.pub" -o /home/huai/.ssh/id_ed25519_lan.pub >/dev/null 2>&1
curl -L "http://10.0.0.21/key/id_ed25519_cloud.pub" -o /home/huai/.ssh/id_ed25519_cloud.pub >/dev/null 2>&1
curl -L "http://10.0.0.21/key/authorized_keys" -o /home/huai/.ssh/authorized_keys >/dev/null 2>&1
curl -s "http://10.0.0.21/key/bite_os_public_20260331.asc" | gpg --import >/dev/null 2>&1

systemctl --user daemon-reload && systemctl --user enable --now pipewire wireplumber ssh-agent shutdown >/dev/null 2>&1
# [ -f /etc/krb5.conf ] && sudo sed -i 's/^/#/' /etc/krb5.conf
sudo tee /etc/krb5.conf </dev/null
