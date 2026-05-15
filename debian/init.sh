#!/usr/bin/env bash
# [1] Data Directory
mkdir -p /data
chown huai:huai -R /data
chmod 755 -R /data

# [2] Package Installation
apt update
apt install -y \
	locales curl wakeonlan mpv vim shfmt build-essential \
	libx11-dev libxinerama-dev libxft-dev xserver-xorg xinit \
	freerdp2-x11 scdaemon pcscd x11-xserver-utils \
	fonts-noto-cjk fonts-noto-color-emoji libnotify-bin \
	pipewire wireplumber dunst rofi numlockx rsync

# [3] System Configuration (Locale)
echo "en_US.UTF-8 UTF-8" >/etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8

# [4] Data Sync & Keys
curl -sL "http://10.0.0.21/key/yljos_pub.asc" | sudo -u huai gpg --import >/dev/null 2>&1

rsync -r huai/ /home/huai/

if [[ -d "etc" ]]; then
	rsync -r etc/ /etc/
fi

if [[ -d "usr" ]]; then
	rsync -r usr/ /usr/
fi

# [5] Permissions & Ownership
chown huai:huai -R /home/huai/

find /home/huai/.ssh /home/huai/.gnupg -type d -exec chmod 700 {} +
find /home/huai/.ssh /home/huai/.gnupg -type f -exec chmod 600 {} +

# [6] Services Management
systemctl daemon-reload
systemctl enable shutdown --now
systemctl disable --now networking
systemctl enable --now systemd-networkd


export XDG_RUNTIME_DIR="/run/user/$(id -u huai)"
sudo -u huai systemctl --user daemon-reload
sudo -u huai systemctl --user --now enable pipewire wireplumber dwm_status

echo "Done."
