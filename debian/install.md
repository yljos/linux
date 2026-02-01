# dwl
sudo apt install  build-essential pkg-config libwlroots-0.18-dev libwayland-dev libxkbcommon-dev libinput-dev libxcb1-dev libxcb-icccm4-dev wayland-protocols
sudo apt install libfcft-dev libpixman-1-dev    
# dwm
sudo apt install build-essential libx11-dev libxinerama-dev libxft-dev
sudo apt install xserver-xorg xinit
sudo apt install freerdp3-x11
xfreerdp /v:IP地址 /u:用户名 /p:密码 /f /sound /clipboard /dynamic-resolution
# 
apt update && apt install sudo
usermod -aG sudo huai
apt install git curl vim  
apt install pipewire pipewire-pulse pipewire-alsa wireplumber
systemctl --user --now enable pipewire pipewire-pulse wireplumber
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