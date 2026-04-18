# Debian System Setup Notes

## 1. Window Managers

### dependencies run as root
```bash
apt install build-essential libx11-dev libxinerama-dev libxft-dev xserver-xorg xinit freerdp2-x11 scdaemon pcscd sudo fonts-noto-cjk fonts-noto-color-emoji git curl vim libnotify-bin arp-scan psmisc pipewire wireplumber pipewire-pulse pipewire-alsa systemd-boot efibootmgr
```

## 2. System Base & Core Tools

### User & Localization run as root
```bash
usermod -aG sudo huai
```

### configure locales and fonts
```bash
sudo dpkg-reconfigure locales
```

### vim plug
```bash
curl -fLo ~/.vim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
```

### mute login message
```bash
touch ~/.hushlogin
```

## 3. Multimedia & Audio (Pipewire)

### enable services for current user
```bash
systemctl --user --now enable pipewire wireplumber
```

## 4. Bootloader (systemd-boot)

### Preparation
```bash
cat /etc/machine-id
cat /proc/cmdline | sudo tee /etc/kernel/cmdline
```

### Edit Kernel Parameters
Use **Vim** to edit `/etc/kernel/cmdline`:
* **Remove**: `BOOT_IMAGE=/boot/vmlinuz-xxx` and `initrd=/boot/initrd.img-xxx`
* **Keep**: `root=UUID=...` and `ro quiet`

### Installation & Grub Purge
```bash
sudo bootctl install
sudo kernel-install add $(uname -r) /boot/vmlinuz-$(uname -r)
```

### verify and reboot
```bash
ls /boot/efi/loader/entries/
systemctl reboot
```

### completely remove grub
```bash
sudo apt purge grub*
sudo apt purge grub-efi-amd64-signed grub-common grub-efi-amd64 grub2-common shim-signed --allow-remove-essential
sudo rm -rf /boot/grub
```

### management
```bash
vim /boot/efi/loader/loader.conf
sudo efibootmgr
sudo efibootmgr -b 0001 -B
```

## 5. Input Method (Fcitx5)
```bash
sudo apt update
sudo apt install fcitx5 fcitx5-rime fcitx5-frontend-gtk3 fcitx5-frontend-gtk4 fcitx5-frontend-qt5
```

## 6. Stow
```bash
mkdir -p ~/.ssh && mkdir -p ~/.gnupg
```

### Environment Variables
Use **Vim** to edit `/etc/environment`:
```text
GTK_IM_MODULE=fcitx
QT_IM_MODULE=fcitx
XMODIFIERS=@im=fcitx
```

### auto umount /data
```bash
crontab -e
 mountpoint -q /data && ! fuser -s /data && fusermount3 -u /data
```

### APT Configuration
# Overwrite configuration to ensure 'apt' binary defaults are strictly overridden
```bash
sudo tee /etc/apt/apt.conf.d/99-disable-progress-bar > /dev/null << 'EOF'
Dpkg::Progress-Fancy "0";
Dpkg::Use-Pty "0";
Binary::apt::Dpkg::Progress-Fancy "0";
Binary::apt::Dpkg::Use-Pty "0";
EOF
```