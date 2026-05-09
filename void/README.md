# Linux EFISTUB (NVRAM) Migration Guide

## 1. Initial File Deployment
Manually sync the current kernel and initrd to a static directory within the EFI System Partition (ESP).

```bash
# Set target directory (e.g., /boot/efi/EFI/void)
TARGET_DIR="/boot/efi/EFI/void"

# Create the directory
sudo mkdir -p "/boot/efi/EFI/void"

# Copy kernel and initrd to static filenames
sudo cp -f /boot/vmlinuz-$(uname -r) "/boot/efi/EFI/void/vmlinuz"
sudo cp -f /boot/initrd-$(uname -r).img "/boot/efi/EFI/void/initrd.img"
```

## 2. NVRAM Boot Entry Creation
Use `efibootmgr` to register the kernel as a standalone EFI application in the motherboard NVRAM.

```bash
# Replace placeholders with actual values
blkid
sudo efibootmgr --create --disk /dev/nvme0p1 --part 1 --label "void" \
    --loader /EFI/void/vmlinuz \
    --unicode "root=UUID=[ROOT_UUID] ro quiet initrd=/EFI/void/initramfs.img"
```

## 3. Cleanup
After confirming `efibootmgr -v` shows `BootCurrent` matches your new entry, remove the legacy bootloader.

```bash
# 1. Remove bootloader packages (e.g., grub or systemd-boot)
# 2. Delete legacy NVRAM entries
sudo efibootmgr -b 0007 -B

```

sudo xbps-install -Su gnupg2-scdaemon
sudo xbps-remove -R grub-x86_64-efi grub
sudo xbps-install -S base-devel libX11-devel libXft-devel libXinerama-devel
sudo xbps-install -S xinit xorg-server font-hack-ttf
sudo xbps-install -S xf86-input-libinput
sudo xbps-install -S intel-media-driver libva-utils
sudo xbps-install -S alsa-utils
sudo xbps-install -S noto-fonts-cjk font-hack-ttf
sudo xbps-install -S yubikey-manager
sudo xbps-install -S dbus
