# Debian System Setup Notes

## 1. Window Managers
### dwm dependencies
sudo apt install build-essential libx11-dev libxinerama-dev libxft-dev xserver-xorg xinit freerdp2-x11 scdaemon pcscd
## 2. System Base & Core Tools
### User & Localization
apt update && apt install sudo
usermod -aG sudo huai
### configure locales and fonts
sudo dpkg-reconfigure locales
sudo apt install fonts-noto-cjk fonts-noto-color-emoji
### Essential Packages
sudo apt install git curl vim nfs-common libnotify-bin arp-scan
### vim plug
curl -fLo ~/.vim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
### mute login message
touch ~/.hushlogin
## 3. Multimedia & Audio (Pipewire)
### install audio stack
sudo apt install pipewire wireplumber pipewire-pulse pipewire-alsa
### enable services for current user
systemctl --user --now enable pipewire wireplumber
## 4. Bootloader (systemd-boot)
### Preparation
sudo apt install systemd-boot efibootmgr
cat /etc/machine-id
cat /proc/cmdline | sudo tee /etc/kernel/cmdline
### Edit Kernel Parameters
Use **Vim** to edit `/etc/kernel/cmdline`:
* **Remove**: `BOOT_IMAGE=/boot/vmlinuz-xxx` and `initrd=/boot/initrd.img-xxx`
* **Keep**: `root=UUID=...` and `ro quiet`

### Installation & Grub Purge
sudo bootctl install
sudo kernel-install add $(uname -r) /boot/vmlinuz-$(uname -r)
### verify and reboot
ls /boot/efi/loader/entries/
systemctl reboot
### completely remove grub
sudo apt purge grub*
sudo apt purge grub-efi-amd64-signed grub-common grub-efi-amd64 grub2-common shim-signed --allow-remove-essential
sudo rm -rf /boot/grub
### management
vim /boot/efi/loader/loader.conf
sudo efibootmgr
sudo efibootmgr -b 0001 -B
## 5. Input Method (Fcitx5)
sudo apt update
sudo apt install fcitx5 fcitx5-rime fcitx5-frontend-gtk3 fcitx5-frontend-gtk4 fcitx5-frontend-qt5
## 6. Stow
mkdir -p ~/.ssh && mkdir -p ~/.gnupg

### Environment Variables
Use **Vim** to edit `/etc/environment`:
text
GTK_IM_MODULE=fcitx
QT_IM_MODULE=fcitx
XMODIFIERS=@im=fcitx
