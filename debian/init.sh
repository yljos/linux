#!/usr/bin/env bash

# Update package list
sudo apt update

# Install minimal X11, build tools, fonts, and utilities
sudo apt install --no-install-recommends \
    xserver-xorg-core xserver-xorg-input-all xserver-xorg-video-all xinit \
    build-essential libx11-dev libxft-dev libxinerama-dev \
    git vim ca-certificates rsync nfs-common \
    fonts-noto-cjk fonts-hack gpg \
    freerdp2-x11 x11-xserver-utils arp-scan mpv \
    pipewire wireplumber pipewire-pulse pipewire-alsa efibootmgr shfmt \
    wakeonlan curl -y

# sudo apt install fcitx5 fcitx5-rime im-config fcitx5-frontend-gtk2 fcitx5-frontend-gtk3 fcitx5-frontend-qt5 -y

# Update font cache
fc-cache -fv



