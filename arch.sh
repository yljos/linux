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
echo "Press Enter to continue or Ctrl+C to cancel..."
read

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
	(
		echo g           # Create new GPT partition table
		echo n           # Create new partition 1 (EFI partition)
		echo 1           # Partition number
		echo             # Default starting sector
		echo +512m       # Size 512m
		echo n           # Create new partition 2 (Swap partition)
		echo 2           # Partition number (changed from 3 to 2)
		echo             # Default starting sector
		echo +$SWAP_SIZE # Use command line parameter for size
		echo n           # Create new partition 3 (Root partition)
		echo 3           # Partition number (changed from 2 to 3)
		echo             # Default starting sector
		echo             # Use all remaining space
		echo t           # Change partition type
		echo 1           # EFI partition
		echo 1           # Select EFI system partition type
		echo t           # Change partition type
		echo 2           # Swap partition (changed from 3 to 2)
		echo 19          # Select Linux swap type
		echo w           # Write partition table and exit
	) | fdisk $DISK

	echo ">> Formatting partitions"
	mkfs.fat -F32 "${DISK}${PART_PREFIX}1" # EFI partition
	mkfs.ext4 "${DISK}${PART_PREFIX}3" -F  # Root partition (changed from 2 to 3)
	mkswap "${DISK}${PART_PREFIX}2"        # Swap partition (changed from 3 to 2)
	swapon "${DISK}${PART_PREFIX}2"        # Enable Swap (changed from 3 to 2)

	echo ">> checking and installing reflector"
	if ! command -v reflector &>/dev/null; then
		echo "Installing reflector..."
		pacman -Sy --noconfirm reflector
	fi
	echo ">> Updating mirror list"
	sudo reflector -c China -a 12 -p https --score 5 --sort rate -n 3 --ipv4 --save /etc/pacman.d/mirrorlist

	# Show the updated mirror list
	echo ">> Updated mirrors:"
	cat /etc/pacman.d/mirrorlist

	echo ">> Mounting partitions"
	mount "${DISK}${PART_PREFIX}3" /mnt
	mkdir -p /mnt/boot && mount "${DISK}${PART_PREFIX}1" /mnt/boot
}

install_packages() {
	echo ">> Installing packages"
	pacman-key --init
	pacman-key --populate archlinux

	pacstrap /mnt base base-devel iptables-nft linux-lts linux-lts-headers linux-firmware vim dhcpcd git less \
		fuzzel swww dunst foot polkit \
		nfs-utils fastfetch btop pipewire pipewire-jack pipewire-alsa pipewire-pulse pavucontrol \
		fcitx5 fcitx5-rime fcitx5-configtool rsync ntfs-3g curl p7zip ranger reflector libnotify openssh \
		mpd mpc freerdp xf86-video-intel libva libva-intel-driver intel-media-driver mpv arp-scan unzip \
		ttf-liberation terminus-font fontconfig wakeonlan noto-fonts noto-fonts-cjk noto-fonts-extra noto-fonts-emoji \
		sox libva-utils telegram-desktop ufw bc firejail nodejs stow firefox w3m mutt black shfmt dash zsh

	echo ">> Generating fstab"
	genfstab -U /mnt >>/mnt/etc/fstab
}
install_packages_nas() {
	echo ">> Installing packages for NAS"
	pacman-key --init
	pacman-key --populate archlinux

	pacstrap /mnt base base-devel iptables-nft nfs-utils linux-lts linux-lts-headers linux-firmware vim dhcpcd git \
		rsync openssh polkit p7zip ranger curl samba mdadm unzip ufw podman dash zsh

	echo ">> Generating fstab"
	genfstab -U /mnt >>/mnt/etc/fstab
}

configure_system() {
	echo ">> Configuring system"
	ROOT_UUID=$(blkid -s UUID -o value "${DISK}${PART_PREFIX}3")
	arch-chroot /mnt env ROOT_UUID="$ROOT_UUID" HOSTNAME="$HOSTNAME" USERNAME="$USERNAME" UCODE="$UCODE" /bin/bash -c '
    echo "The root UUID is: $ROOT_UUID"
    echo "Hostname: $HOSTNAME"
    echo "Username: $USERNAME"
    echo "CPU Microcode: $UCODE"
    sleep 5

    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
    hwclock --systohc

    echo -e "en_US.UTF-8 UTF-8" > /etc/locale.gen
    locale-gen
    echo "LANG=en_US.UTF-8" > /etc/locale.conf

    echo "$HOSTNAME" > /etc/hostname
    echo -e "127.0.0.1       localhost\n::1             localhost\n127.0.0.1       $HOSTNAME.localdomain  $HOSTNAME" > /etc/hosts
    echo "#192.168.31.21:/ /home/$USERNAME/data nfs4 _netdev,noauto,x-systemd.automount,x-systemd.mount-timeout=10,x-systemd.idle-timeout=10,timeo=14,rsize=1048576,wsize=1048576 0 0" >> /etc/fstab

    echo "root:1" | chpasswd

    pacman -S --noconfirm efibootmgr $UCODE
    bootctl install --path=/boot

    echo ">> Setting up loader configuration"
    echo "default arch.conf" > /boot/loader/loader.conf
    echo "# timeout 5" >> /boot/loader/loader.conf
    echo "# editor no" >> /boot/loader/loader.conf

    echo "title   Arch Linux" > /boot/loader/entries/arch.conf
    echo "linux   /vmlinuz-linux-lts" >> /boot/loader/entries/arch.conf
    echo "initrd  /${UCODE}.img" >> /boot/loader/entries/arch.conf
    echo "initrd  /initramfs-linux-lts.img" >> /boot/loader/entries/arch.conf
    echo "options root=UUID=$ROOT_UUID rw quiet" >> /boot/loader/entries/arch.conf
   
    echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    echo "$USERNAME:1" | chpasswd
    systemctl enable systemd-homed --now
    homectl create $USERNAME --storage=luks --disk-size=60G --uid=1000 --member-of=wheel --shell=/usr/bin/bash --password "1"
    echo -e "#GTK_IM_MODULE=fcitx\nQT_IM_MODULE=fcitx\nXMODIFIERS=@im=fcitx\nSDL_IM_MODULE=fcitx\nGLFW_IM_MODULE=fcitx" >> /etc/environment

    echo ">> Enabling system services"
    systemctl enable dhcpcd
    ufw enable
    systemctl enable ufw 
    '
}

configure_system_nas() {
	echo ">> Configuring system for NAS"
	ROOT_UUID=$(blkid -s UUID -o value "${DISK}${PART_PREFIX}3")
	arch-chroot /mnt env ROOT_UUID="$ROOT_UUID" HOSTNAME="$HOSTNAME" USERNAME="$USERNAME" UCODE="$UCODE" /bin/bash -c '
    echo "The root UUID is: $ROOT_UUID"
    echo "Hostname: $HOSTNAME"
    echo "Username: $USERNAME"
    echo "CPU Microcode: $UCODE"
    sleep 5

    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
    hwclock --systohc

    echo -e "en_US.UTF-8 UTF-8" > /etc/locale.gen
    locale-gen
    echo "LANG=en_US.UTF-8" > /etc/locale.conf

    echo "$HOSTNAME" > /etc/hostname
    echo -e "127.0.0.1       localhost\n::1             localhost\n127.0.0.1       $HOSTNAME.localdomain  $HOSTNAME" > /etc/hosts
    echo "root:1" | chpasswd

    pacman -S --noconfirm efibootmgr $UCODE
    bootctl install --path=/boot

    echo ">> Setting up loader configuration"
    echo "default nas.conf" > /boot/loader/loader.conf
    echo "# timeout 5" >> /boot/loader/loader.conf
    echo "# editor no" >> /boot/loader/loader.conf

    echo "title   Nas" > /boot/loader/entries/nas.conf
    echo "linux   /vmlinuz-linux-lts" >> /boot/loader/entries/nas.conf
    echo "initrd  /${UCODE}.img" >> /boot/loader/entries/nas.conf
    echo "initrd  /initramfs-linux-lts.img" >> /boot/loader/entries/nas.conf
    echo "options root=UUID=$ROOT_UUID rw quiet" >> /boot/loader/entries/nas.conf

    useradd -m -G wheel $USERNAME
    echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    echo "$USERNAME:1" | chpasswd

    echo ">> Enabling system services"
    systemctl enable dhcpcd
    systemctl enable sshd
    loginctl enable-linger $USERNAME
    '
}

# Main process flow
setup_partitions

# Choose package set based on hostname
if [[ "$HOSTNAME" == "nas" ]]; then
	echo ">> NAS configuration detected, installing NAS packages"
	install_packages_nas
	configure_system_nas
else
	echo ">> Desktop configuration detected, installing desktop packages"
	install_packages
	configure_system
fi

# Add before script ends
echo "
====================================
    INSTALLATION COMPLETED!
====================================

System has been installed successfully!

====================================
"
# Give user some time to read the information
sleep 3

# Clean up and reboot
echo ">> Cleaning up and rebooting"
umount -R /mnt
reboot
