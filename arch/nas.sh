#!/usr/bin/env bash
set -e

DISK="/dev/mmcblk0"
HOSTNAME="Nas"
USERNAME="huai"
UCODE="intel-ucode"

wipefs -a "$DISK"
sfdisk "$DISK" <<EOF
label: gpt
size=512M, type=U
type=L
EOF

sleep 2
mkfs.fat -F32 "${DISK}p1"
mkfs.ext4 "${DISK}p2" -F

mount "${DISK}p2" /mnt
mkdir -p /mnt/boot && mount "${DISK}p1" /mnt/boot

# echo 'Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch' >/etc/pacman.d/mirrorlist
reflector -c China --latest 3 --protocol https --sort rate --save /etc/pacman.d/mirrorlist
pacman-key --init
pacman-key --populate archlinux

pacstrap /mnt base linux-lts linux-firmware vim git btop rsync openssh nfs-utils samba mdadm ttf-hack dhcpcd

genfstab -U /mnt >>/mnt/etc/fstab

ROOT_UUID=$(blkid -s UUID -o value "${DISK}p2")

# Pass DISK to the chroot environment for efibootmgr
arch-chroot /mnt env ROOT_UUID="$ROOT_UUID" HOSTNAME="$HOSTNAME" USERNAME="$USERNAME" UCODE="$UCODE" DISK="$DISK" /bin/bash -c '
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
hwclock --systohc

echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

echo "$HOSTNAME" > /etc/hostname
echo -e "127.0.0.1\tlocalhost\n::1\tlocalhost\n127.0.0.1\t$HOSTNAME.localdomain\t$HOSTNAME" > /etc/hosts

echo "root:1" | chpasswd
useradd -M -s /usr/bin/nologin "$USERNAME"
mkdir -p /data 
chmod 755 -R /data
mkdir -p /podman

pacman -S --noconfirm efibootmgr $UCODE

# Direct EFISTUB NVRAM entry
efibootmgr --create --disk "$DISK" --part 1 --label "NAS" --loader /vmlinuz-linux-lts --unicode "root=UUID=$ROOT_UUID rw initrd=\\${UCODE}.img initrd=\\initramfs-linux-lts.img quiet"

echo "$USERNAME:1" | chpasswd

systemctl enable sshd dhcpcd
'
umount -R /mnt
reboot
