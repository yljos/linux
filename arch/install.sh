#!/usr/bin/env bash

# Default values
DISK="/dev/nvme0n1"
HOSTNAME="Arch"
USERNAME="huai"
SWAP_SIZE="16384M"
PART_PREFIX="" # Will be set based on device type
UCODE=""       # Will be set based on CPU detection

# Add help option
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -d DEVICE   Set installation disk (default: /dev/nvme0n1)"
    echo "  -h NAME     Set hostname (default: Arch)"
    echo "  -u USER     Set username (default: huai)"
    echo "  -s SIZE     Set swap size (default: 16384M)"
    echo "  -?          Show this help message"
    exit 0
}

# Parse command line arguments
while getopts "d:h:u:s:?" opt; do
    case $opt in
    d) DISK="$OPTARG" ;;
    h) HOSTNAME="$OPTARG" ;;
    u) USERNAME="$OPTARG" ;;
    s) SWAP_SIZE="$OPTARG" ;;
    \?) usage ;;
    esac
done

# Detect device type and set partition prefix
detect_device_type() {
    if [[ $DISK == *"nvme"* ]] || [[ $DISK == *"mmcblk"* ]]; then
        PART_PREFIX="p"
        echo ">> NVMe/MMC device detected, using partition format: ${DISK}p1"
    else
        PART_PREFIX=""
        echo ">> Standard device detected, using partition format: ${DISK}1"
    fi
}

# Detect CPU type and set microcode package
detect_cpu_type() {
    if grep -q "GenuineIntel" /proc/cpuinfo; then
        UCODE="intel-ucode"
        echo ">> Intel CPU detected, will install intel-ucode"
    elif grep -q "AuthenticAMD" /proc/cpuinfo; then
        UCODE="amd-ucode"
        echo ">> AMD CPU detected, will install amd-ucode"
    else
        UCODE="intel-ucode"
        echo ">> CPU type not detected, defaulting to intel-ucode"
    fi
}

# Display the configuration to be used
echo "Will use the following configuration:"
echo "Disk: $DISK"
echo "Hostname: $HOSTNAME"
echo "Username: $USERNAME"
echo "Swap size: $SWAP_SIZE"
sleep 6

# Add error handling function
set -e # Exit immediately if any command fails
error_handler() {
    echo "Error occurred on line $1"
    exit 1
}
trap 'error_handler ${LINENO}' ERR

# Add disk device check at the beginning of the script
if [ ! -b "$DISK" ]; then
    echo "Error: Device $DISK does not exist"
    exit 1
fi

# Detect device type and CPU type
detect_device_type
detect_cpu_type

# Set time synchronization
echo ">> Enabling NTP time synchronization"
timedatectl set-ntp true

# Split functionality into functions
setup_partitions() {
    echo ">> Partitioning disk $DISK"
    wipefs -a "$DISK"
    sfdisk "$DISK" <<EOF
label: gpt
size=512M, type=U
size=$SWAP_SIZE, type=S
type=L
EOF

    echo ">> Formatting partitions"
    sleep 2 # Add a short delay to ensure the system recognizes the new partitions
    mkfs.fat -F32 "${DISK}${PART_PREFIX}1" # EFI partition
    mkfs.ext4 "${DISK}${PART_PREFIX}3" -F  # Root partition
    mkswap "${DISK}${PART_PREFIX}2"        # Swap partition
    swapon "${DISK}${PART_PREFIX}2"        # Enable Swap

    echo ">> Configuring Tsinghua University mirror"
    echo 'Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch' >/etc/pacman.d/mirrorlist

    echo ">> Mounting partitions"
    mount "${DISK}${PART_PREFIX}3" /mnt
    mkdir -p /mnt/boot && mount "${DISK}${PART_PREFIX}1" /mnt/boot
}

install_packages() {
    echo ">> Installing packages"
    pacman-key --init
    pacman-key --populate archlinux

    pacstrap /mnt base base-devel iptables-nft linux-lts linux-lts-headers linux-firmware vim git less \
        rofi dunst alacritty polkit \
        fastfetch btop pipewire wireplumber pipewire-pulse pipewire-alsa rtkit \
        rsync ntfs-3g curl p7zip libnotify openssh sshfs \
        freerdp libva libva-intel-driver intel-media-driver mpv arp-scan unzip \
        ttf-liberation fontconfig wakeonlan noto-fonts noto-fonts-cjk noto-fonts-extra noto-fonts-emoji \
        libva-utils telegram-desktop bc firejail nodejs stow firefox python-black shfmt \
        cloudflared xorg-server xorg-xinit
    echo ">> Generating fstab"
    genfstab -U /mnt >>/mnt/etc/fstab
}
# dwl
# wlroots0.18 tllist fcft wayland-protocols wayland fuzzel mako foot
# dwm
# xorg-server xorg-xinit
configure_system() {
    echo ">> Configuring system"
    ROOT_UUID=$(blkid -s UUID -o value "${DISK}${PART_PREFIX}3")
    arch-chroot /mnt env ROOT_UUID="$ROOT_UUID" HOSTNAME="$HOSTNAME" USERNAME="$USERNAME" UCODE="$UCODE" /bin/bash -c '
    echo "The root UUID is: $ROOT_UUID"
    echo "Hostname: $HOSTNAME"
    echo "Username: $USERNAME"
    echo "CPU Microcode: $UCODE"
    sleep 5

    ln -sf /usr/share/zoneinfo/UTC /etc/localtime
    hwclock --systohc

    echo -e "en_US.UTF-8 UTF-8" > /etc/locale.gen
    locale-gen
    echo "LANG=en_US.UTF-8" > /etc/locale.conf

    echo "$HOSTNAME" > /etc/hostname
    echo -e "127.0.0.1       localhost\n::1             localhost\n127.0.0.1       $HOSTNAME.localdomain  $HOSTNAME" > /etc/hosts

    echo -e "[Time]\nNTP=ntp.aliyun.com" > /etc/systemd/timesyncd.conf

    # Write network configuration files manually
    echo ">> Writing network configurations"
    
    cat <<EOF > /etc/systemd/network/10-lo.network
[Match]
Name=lo

[Network]
Address=127.0.0.1/8
Address=::1/128
EOF

    cat <<EOF > /etc/systemd/network/20-enp0s31f6.network
[Match]
Name=enp0s31f6

[Network]
Address=10.0.0.25/24
Gateway=10.0.0.1

[Link]
RequiredForOnline=routable
EOF

    cat <<EOF > /etc/systemd/network/30-wlp2s0.network
[Match]
Name=wlp2s0
[Link]
ActivationPolicy=down
Unmanaged=yes
EOF

    echo "root:1" | chpasswd
    useradd -m -G wheel "$USERNAME"
    mkdir -p /data
    mkdir -p /home/$USERNAME/.config
    mkdir -p /home/$USERNAME/.gnupg
    mkdir -p /home/$USERNAME/.ssh
    chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh
    chown -R $USERNAME:$USERNAME /home/$USERNAME/.config
    chown -R $USERNAME:$USERNAME /home/$USERNAME/.gnupg
    chown -R $USERNAME:$USERNAME /data
    chmod 755 -R /data
    chmod 700 -R /home/$USERNAME/.gnupg
    chmod 700 -R /home/$USERNAME/.ssh

    pacman -S --noconfirm efibootmgr $UCODE
    bootctl install --path=/boot

    echo ">> Setting up loader configuration"
    echo "default arch.conf" > /boot/loader/loader.conf

    echo "title   Arch Linux" > /boot/loader/entries/arch.conf
    echo "linux   /vmlinuz-linux-lts" >> /boot/loader/entries/arch.conf
    echo "initrd  /${UCODE}.img" >> /boot/loader/entries/arch.conf
    echo "initrd  /initramfs-linux-lts.img" >> /boot/loader/entries/arch.conf
    echo "options root=UUID=$ROOT_UUID rw quiet" >> /boot/loader/entries/arch.conf
  
    echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    echo "$USERNAME:1" | chpasswd

    echo ">> Enabling system services"
    systemctl enable systemd-networkd
    systemctl enable sshd
    '
    # DNS configuration outside chroot to ensure chattr takes effect
    echo ">> Locking DNS configuration"
    rm -f /mnt/etc/resolv.conf
    echo "nameserver 1.1.1.1" >/mnt/etc/resolv.conf
    chattr +i /mnt/etc/resolv.conf
}

# Main process flow
setup_partitions
echo ">> System configuration detected, installing packages"
install_packages
configure_system

echo "
====================================
    INSTALLATION COMPLETED!
====================================
"
sleep 3

echo ">> Cleaning up and rebooting"
umount -R /mnt
reboot