#!/usr/bin/env bash



# Update package list and install minimal Xorg, build tools, dependencies, and vim
sudo apt update
sudo apt install --no-install-recommends xserver-xorg-core xserver-xorg-input-all xserver-xorg-video-all xinit build-essential libx11-dev libxft-dev libxinerama-dev git vim ca-certificates

# Install open-source Noto CJK fonts
sudo apt install fonts-noto-cjk fonts-hack

# Update font cache
fc-cache -fv

# freerdp(debian12)
sudo apt install freerdp2-x11 rsync


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

# systemctl daemon-reload
# systemctl enable --now shutdown >/dev/null 2>&1
# systemctl enable --now pcscd.socket

tee /etc/krb5.conf </dev/null

echo "Arch Linux initialization complete."

