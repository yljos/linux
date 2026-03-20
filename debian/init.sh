#!/bin/bash

# ---------------------------------------------------------
# [1] System Update & Base Tools
# ---------------------------------------------------------
sudo apt update
sudo apt install -y sudo git curl vim nfs-common

# Create /data with specific permissions
# This is required for your mount-data function
sudo mkdir -p /data
sudo chown huai:huai /data
sudo chmod 755 /data

# Locale and Fonts
sudo dpkg-reconfigure locales
sudo apt install -y fonts-noto-cjk fonts-noto-color-emoji

# ---------------------------------------------------------
# [2] User Space Directory Structure
# ---------------------------------------------------------
mkdir -p ~/.ssh ~/.gnupg ~/.config/systemd/user
chmod 700 ~/.gnupg

# ---------------------------------------------------------
# [3] DWM & X11 Build Dependencies
# ---------------------------------------------------------
sudo apt install -y \
    build-essential \
    libx11-dev libxinerama-dev libxft-dev \
    xserver-xorg xinit

# ---------------------------------------------------------
# [4] Desktop Services & Audio
# ---------------------------------------------------------
# Audio: Pure Native PipeWire
sudo apt install -y pipewire wireplumber libnotify-bin

# Enable PipeWire services for current user
systemctl --user --now enable pipewire wireplumber

# GPG Smartcard & Secret Management (for your key() function)
sudo apt install -y scdaemon pcscd

# ---------------------------------------------------------
# [5] Remote Desktop & Cleanup
# ---------------------------------------------------------
# Install FreeRDP3
sudo apt install -y freerdp3-x11

# Final Cleanup
sudo apt autoremove -y


