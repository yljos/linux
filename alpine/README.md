# Alpine Linux EFISTUB Migration Guide

## 1. Stage Kernel and Initramfs

```sh
# Copy current kernel and initramfs to the ESP root
cp /boot/vmlinuz-lts /boot/efi/
cp /boot/initramfs-lts /boot/efi/

# Verify staged files
ls -lh /boot/efi/vmlinuz-lts /boot/efi/initramfs-lts
```

## 2. Remount ESP as `/boot`

```sh
# Unmount current ESP mountpoint
umount /boot/efi

# Update /etc/fstab mountpoint from /boot/efi to /boot
sed -i 's|[[:space:]]/boot/efi[[:space:]]| /boot |' /etc/fstab

# Mount updated /boot target
mount /boot

# Verify mount device is /dev/sda1
df -h /boot
```

## 3. Retrieve Root Filesystem UUID

```sh
# Identify root filesystem block device
mount | grep ' / '

# Extract root UUID from the identified device (e.g. /dev/sda3)
blkid -s UUID -o value /dev/sda3
```

## 4. Register EFISTUB Entry

```sh
# Delete stale NVRAM entries
efibootmgr -b 0007 -B
efibootmgr -b 000B -B

# Create EFISTUB boot entry using resolved root UUID
efibootmgr -c -d /dev/sda -p 1 \
  -L "Alpine Linux" \
  -l '\vmlinuz-lts' \
  -u "initrd=\initramfs-lts root=UUID=$(blkid -s UUID -o value /dev/sda3) modules=sd-mod,usb-storage,ext4 quiet"

# Verify BootOrder priority
efibootmgr
```

## 5. Reboot and Verification

```sh
reboot
```

After rebooting, confirm direct firmware execution:

```sh
# Check current active boot entry ID
efibootmgr | grep BootCurrent
```

## 6. Post-Verification GRUB Removal

```sh
# Remove GRUB packages
apk del grub grub-efi

# Remove legacy bootloader files from ESP
rm -rf /boot/EFI/BOOT /boot/EFI/alpine /boot/grub

# Remove obsolete GRUB NVRAM entry
efibootmgr -b 0016 -B
```