#!/bin/bash

# [1] Directories
# ---------------------------------------------------------
mkdir -p /home/huai/.ssh
mkdir -p /home/huai/.gnupg
mkdir -p /home/huai/.config/systemd/user

# Ensure GPG directory is secure
chmod 700 /home/huai/.gnupg

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
sudo apt install -y locales git curl vim nfs-common build-essential \
	libx11-dev libxinerama-dev libxft-dev xserver-xorg xinit \
	freerdp2-x11 scdaemon pcscd \
	fonts-noto-cjk fonts-noto-color-emoji libnotify-bin \
	pipewire wireplumber

# ---------------------------------------------------------
# [4] System Configuration
# ---------------------------------------------------------
# Overwrite locale.gen directly for en_US.UTF-8
echo "en_US.UTF-8 UTF-8" | sudo tee /etc/locale.gen >/dev/null
sudo locale-gen
sudo update-locale LANG=en_US.UTF-8

# Enable audio services
systemctl --user --now enable pipewire wireplumber

# ---------------------------------------------------------
# [5] Network Service Swap
# ---------------------------------------------------------
sudo systemctl disable --now networking
sudo systemctl enable --now systemd-networkd
