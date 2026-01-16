#!/usr/bin/env bash

# Check if reflector is installed
if ! command -v reflector &>/dev/null; then
	echo "reflector is not installed, installing..."
	sudo pacman -S --noconfirm reflector
fi

# Update mirror list
sudo reflector -c China -a 12 -p https --score 5 --sort rate -n 3 --ipv4 --save /etc/pacman.d/mirrorlist &>/dev/null

cat /etc/pacman.d/mirrorlist
