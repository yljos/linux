# Linux EFISTUB (NVRAM) Migration Guide

## 1. Initial File Deployment
Manually sync the current kernel and initrd to a static directory within the EFI System Partition (ESP).

```bash
# Set target directory (e.g., /boot/efi/EFI/[NAME])
TARGET_DIR="/boot/efi/EFI/[NAME]"

# Create the directory
sudo mkdir -p "$TARGET_DIR"

# Copy kernel and initrd to static filenames
sudo cp -f /boot/vmlinuz-$(uname -r) "$TARGET_DIR/vmlinuz"
sudo cp -f /boot/initrd.img-$(uname -r) "$TARGET_DIR/initrd.img"
```

## 2. NVRAM Boot Entry Creation
Use `efibootmgr` to register the kernel as a standalone EFI application in the motherboard NVRAM.

```bash
# Replace placeholders with actual values
sudo efibootmgr --create --disk /dev/ --part 1 --label "[NAME]" \
    --loader /EFI/[NAME]/vmlinuz \
    --unicode "root=UUID=[ROOT_UUID] ro quiet initrd=/EFI/[NAME]/initrd.img"
```

## 3. Cleanup
After confirming `efibootmgr -v` shows `BootCurrent` matches your new entry, remove the legacy bootloader.

```bash
# 1. Remove bootloader packages (e.g., grub or systemd-boot)
# 2. Delete legacy NVRAM entries
sudo efibootmgr -b 0007 -B

```

sudo xbps-install -Su gnupg2-scdaemon
