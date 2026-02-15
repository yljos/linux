# dwl
sudo apt install  build-essential pkg-config libwlroots-0.18-dev libwayland-dev libxkbcommon-dev libinput-dev libxcb1-dev libxcb-icccm4-dev wayland-protocols
sudo apt install libfcft-dev libpixman-1-dev    
# dwm
sudo apt install build-essential libx11-dev libxinerama-dev libxft-dev
sudo apt install xserver-xorg xinit
sudo apt install freerdp2-x11
sudo apt install scdaemon pcscd
# 
apt update && apt install sudo
usermod -aG sudo huai
sudo dpkg-reconfigure locales
sudo apt install fonts-noto-cjk fonts-noto-color-emoji
apt install git curl vim  
#
sudo apt install pipewire wireplumber

sudo apt install pipewire-pulse pipewire-alsa

systemctl --user --now enable pipewire wireplumber
sudo apt install arp-scan

sudo apt install systemd-boot efibootmgr
cat /etc/machine-id              #systemd-machine-id-setup
cat /proc/cmdline | sudo tee /etc/kernel/cmdline
vim /etc/kernel/cmdline
删除 BOOT_IMAGE=/boot/vmlinuz-xxx 开头的部分。

删除 initrd=/boot/initrd.img-xxx 部分。

保留 root=UUID=... 和 ro quiet 等参数
sudo bootctl install
sudo kernel-install add $(uname -r) /boot/vmlinuz-$(uname -r)
ls /boot/efi/loader/entries/
systemctl reboot
sudo apt purge grub*
sudo apt purge grub-efi-amd64-signed grub-common grub-efi-amd64 grub2-common shim-signed --allow-remove-essential
sudo rm -rf /boot/grub
vim /boot/efi/loader/loader.conf
sudo efibootmgr
sudo efibootmgr -b 0001 -B

sudo apt update
sudo apt install fcitx5 fcitx5-rime fcitx5-frontend-gtk3 fcitx5-frontend-gtk4 fcitx5-frontend-qt5

sudo vim /etc/environment

GTK_IM_MODULE=fcitx
QT_IM_MODULE=fcitx
XMODIFIERS=@im=fcitx