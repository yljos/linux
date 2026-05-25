#!/usr/bin/env bash
set -e

DISK="/dev/nvme0n1"
HOSTNAME="Arch"
USERNAME="huai"

# Detect partition prefix and CPU microcode
[[ $DISK == *"nvme"* || $DISK == *"mmcblk"* ]] && P="p" || P=""
grep -q "AuthenticAMD" /proc/cpuinfo && UCODE="amd-ucode" || UCODE="intel-ucode"

wipefs -a "$DISK"
sfdisk "$DISK" <<EOF
label: gpt
size=512M, type=U
type=L
EOF

sleep 2
mkfs.fat -F32 "${DISK}${P}1"
mkfs.ext4 "${DISK}${P}2" -F

mount "${DISK}${P}2" /mnt
mkdir -p /mnt/boot && mount "${DISK}${P}1" /mnt/boot

# echo 'Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch' >/etc/pacman.d/mirrorlist
reflector -c China --latest 3 --protocol https --sort rate --save /etc/pacman.d/mirrorlist
pacman-key --init
pacman-key --populate archlinux

pacstrap /mnt base base-devel iptables-nft linux-lts linux-lts-headers linux-firmware vim git less polkit \
	fastfetch btop pipewire wireplumber pipewire-pulse pipewire-alsa rtkit pcsclite ccid rsync ntfs-3g curl p7zip libnotify openssh nfs-utils \
	freerdp libva libva-intel-driver intel-media-driver libva-utils mpv arp-scan \
	ttf-liberation fontconfig wakeonlan ttf-hack noto-fonts noto-fonts-cjk noto-fonts-extra noto-fonts-emoji \
	telegram-desktop bc firejail nodejs firefox python-black shfmt dhcpcd \
	cloudflared xorg-server xorg-xinit xorg-xsetroot alacritty rofi dunst picom numlockx
genfstab -U /mnt >>/mnt/etc/fstab

ROOT_UUID=$(blkid -s UUID -o value "${DISK}${P}2")

# Pass DISK variable to chroot for efibootmgr
arch-chroot /mnt env ROOT_UUID="$ROOT_UUID" HOSTNAME="$HOSTNAME" USERNAME="$USERNAME" UCODE="$UCODE" DISK="$DISK" /bin/bash -c '
ln -sf /usr/share/zoneinfo/UTC /etc/localtime
hwclock --systohc

echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf

echo "$HOSTNAME" > /etc/hostname
echo -e "127.0.0.1\tlocalhost\n::1\tlocalhost\n127.0.0.1\t$HOSTNAME.localdomain\t$HOSTNAME" > /etc/hosts

echo "root:1" | chpasswd
useradd -m -G wheel "$USERNAME"

mkdir -p /data 
chown -R $USERNAME:$USERNAME /data
chmod 755 -R /data

pacman -S --noconfirm efibootmgr $UCODE

# Create EFISTUB NVRAM boot entry directly using part 1
efibootmgr --create --disk "$DISK" --part 1 --label "Arch" --loader /vmlinuz-linux-lts --unicode "root=UUID=$ROOT_UUID rw quiet initrd=\\${UCODE}.img initrd=\\initramfs-linux-lts.img"

echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
echo "$USERNAME:1" | chpasswd

systemctl enable dhcpcd sshd
'

umount -R /mnt
reboot
