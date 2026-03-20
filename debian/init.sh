# ---------------------------------------------------------
# [1] Directories
# ---------------------------------------------------------
mkdir -p /home/huai/.ssh
mkdir -p /home/huai/.gnupg
mkdir -p /home/huai/.config/systemd/user

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
sudo apt install -y git curl vim nfs-common build-essential \
    libx11-dev libxinerama-dev libxft-dev xserver-xorg xinit \
    freerdp2-x11 freerdp3-x11 scdaemon pcscd \
    fonts-noto-cjk fonts-noto-color-emoji libnotify-bin \
    pipewire wireplumber

# ---------------------------------------------------------
# [4] System Configuration
# ---------------------------------------------------------
sudo dpkg-reconfigure locales
systemctl --user --now enable pipewire wireplumber

# ---------------------------------------------------------
# [5] Network Service Swap
# ---------------------------------------------------------
sudo systemctl disable --now networking
sudo systemctl enable --now systemd-networkd