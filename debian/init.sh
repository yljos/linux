#!/usr/bin/env bash

# Update package list
sudo apt update

# Install minimal X11, build tools, fonts, and utilities
sudo apt install --no-install-recommends \
    xserver-xorg-core xserver-xorg-input-all xserver-xorg-video-all xinit \
    build-essential libx11-dev libxft-dev libxinerama-dev \
    git vim ca-certificates rsync nfs-common \
    fonts-noto-cjk fonts-hack \
    freerdp2-x11 x11-xserver-utils

# Update font cache
fc-cache -fv

