#!/bin/bash

# ---------------------------------------------------------
# [1] Directories & Dotfiles
# ---------------------------------------------------------
mkdir -p /home/huai/.ssh \
	/home/huai/.gnupg \
	/home/huai/.config/systemd/user

# Ensure GPG directory is secure
chmod 700 /home/huai/.gnupg

# Manage dotfiles via stow
rm -f /home/huai/.bashrc

# ---------------------------------------------------------
# [2] Data Directory
# ---------------------------------------------------------
sudo mkdir -p /data
sudo chown huai:huai /data
sudo chmod 755 /data

# ---------------------------------------------------------
# [3] Package Installation
# ---------------------------------------------------------
sudo apt update
sudo apt install -y \
	locales git curl vim stow shfmt build-essential \
	libx11-dev libxinerama-dev libxft-dev xserver-xorg xinit \
	freerdp2-x11 scdaemon pcscd x11-xserver-utils \
	fonts-noto-cjk fonts-noto-color-emoji libnotify-bin \
	pipewire wireplumber dunst rofi numlockx

systemctl --user daemon-reload

# ---------------------------------------------------------
# [4] System Configuration
# ---------------------------------------------------------
# Overwrite locale.gen directly for en_US.UTF-8
echo "en_US.UTF-8 UTF-8" | sudo tee /etc/locale.gen >/dev/null
sudo locale-gen
sudo update-locale LANG=en_US.UTF-8

# Enable audio services
systemctl --user --now enable pipewire wireplumber dwm-status shutdown

# ---------------------------------------------------------
# [5] Network Service Swap
# ---------------------------------------------------------
sudo systemctl disable --now networking
sudo systemctl enable --now systemd-networkd

# ---------------------------------------------------------
# [6] Git Configuration
# ---------------------------------------------------------
git config --global core.editor "vim"
git config --global user.signingkey CABB8B2144528A69
git config --global commit.gpgsign true
git config --global user.name "bite-os"
git config --global user.email "bite-os@biteos.org"

# ---------------------------------------------------------
# [7] SSH & GPG Keys
# ---------------------------------------------------------
URL="http://10.0.0.21/key"
SSH="/home/huai/.ssh"

curl -sL "${URL}/id_ed25519_lan.gpg" -o "${SSH}/id_ed25519_lan.gpg" >/dev/null 2>&1
curl -sL "${URL}/id_ed25519_cloud.gpg" -o "${SSH}/id_ed25519_cloud.gpg" >/dev/null 2>&1
curl -sL "${URL}/id_ed25519_lan.pub" -o "${SSH}/id_ed25519_lan.pub" >/dev/null 2>&1
curl -sL "${URL}/id_ed25519_cloud.pub" -o "${SSH}/id_ed25519_cloud.pub" >/dev/null 2>&1
curl -sL "${URL}/authorized_keys" -o "${SSH}/authorized_keys" >/dev/null 2>&1

curl -sL "${URL}/bite_os_public_20260331.asc" | gpg --import >/dev/null 2>&1
