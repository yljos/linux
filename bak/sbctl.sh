#!/usr/bin/env bash

# Define color variables
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # Reset color

echo -e "${BLUE}===== Starting Secure Boot Configuration =====${NC}"
sleep 1

# Kernel selection
echo -e "${BLUE}Select kernel to use:${NC}"
echo -e "1) Regular kernel (linux)"
echo -e "2) LTS kernel (linux-lts)"
echo -e "3) Auto detect (sign existing kernel)"
read -p "Choose option (1-3): " kernel_choice

echo -e "${YELLOW}Creating Secure Boot keys...${NC}"
sudo sbctl create-keys
sleep 3

echo -e "${YELLOW}Enrolling keys to UEFI...${NC}"
sudo sbctl enroll-keys -m
sleep 3

echo -e "${YELLOW}Signing bootloader file...${NC}"
sudo sbctl sign -s /boot/EFI/BOOT/BOOTX64.EFI
sleep 3

echo -e "${YELLOW}Signing systemd-boot...${NC}"
sudo sbctl sign -s /boot/EFI/systemd/systemd-bootx64.efi
sleep 3

echo -e "${YELLOW}Signing Linux kernels...${NC}"

case $kernel_choice in
1)
	# Use regular kernel
	if [ -f /boot/vmlinuz-linux ]; then
		echo -e "${YELLOW}Signing regular kernel...${NC}"
		sudo sbctl sign -s /boot/vmlinuz-linux

		# Remove LTS kernel signature if exists
		if sudo sbctl list-files | grep -q "vmlinuz-linux-lts"; then
			echo -e "${RED}Removing LTS kernel signature...${NC}"
			sudo sbctl remove-file /boot/vmlinuz-linux-lts
		fi
	else
		echo -e "${RED}Regular kernel not found!${NC}"
	fi
	;;
2)
	# Use LTS kernel
	if [ -f /boot/vmlinuz-linux-lts ]; then
		echo -e "${YELLOW}Signing LTS kernel...${NC}"
		sudo sbctl sign -s /boot/vmlinuz-linux-lts

		# Remove regular kernel signature if exists
		if sudo sbctl list-files | grep -q "vmlinuz-linux" && ! sudo sbctl list-files | grep -q "vmlinuz-linux-lts"; then
			echo -e "${RED}Removing regular kernel signature...${NC}"
			sudo sbctl remove-file /boot/vmlinuz-linux
		fi
	else
		echo -e "${RED}LTS kernel not found!${NC}"
	fi
	;;
3)
	# Auto detect - original logic
	if [ -f /boot/vmlinuz-linux ]; then
		echo -e "${YELLOW}Signing regular kernel...${NC}"
		sudo sbctl sign -s /boot/vmlinuz-linux

		# Auto remove LTS kernel signature if it doesn't exist
		if [ ! -f /boot/vmlinuz-linux-lts ] && sudo sbctl list-files | grep -q "vmlinuz-linux-lts"; then
			echo -e "${RED}Auto removing old LTS kernel signature...${NC}"
			sudo sbctl remove-file /boot/vmlinuz-linux-lts
		fi
	elif [ -f /boot/vmlinuz-linux-lts ]; then
		echo -e "${YELLOW}Signing LTS kernel...${NC}"
		sudo sbctl sign -s /boot/vmlinuz-linux-lts

		# Auto remove regular kernel signature if it doesn't exist
		if [ ! -f /boot/vmlinuz-linux ] && sudo sbctl list-files | grep -q "vmlinuz-linux"; then
			echo -e "${RED}Auto removing old regular kernel signature...${NC}"
			sudo sbctl remove-file /boot/vmlinuz-linux
		fi
	else
		echo -e "${RED}No kernel found!${NC}"
	fi
	;;
*)
	echo -e "${RED}Invalid choice, using auto detect...${NC}"
	# Fall back to auto detect logic
	if [ -f /boot/vmlinuz-linux ]; then
		echo -e "${YELLOW}Signing regular kernel...${NC}"
		sudo sbctl sign -s /boot/vmlinuz-linux
	elif [ -f /boot/vmlinuz-linux-lts ]; then
		echo -e "${YELLOW}Signing LTS kernel...${NC}"
		sudo sbctl sign -s /boot/vmlinuz-linux-lts
	else
		echo -e "${RED}No kernel found!${NC}"
	fi
	;;
esac

sleep 3

echo -e "${YELLOW}Verifying signature status...${NC}"
sudo sbctl verify
sleep 3

echo -e "${YELLOW}Enabling systemd-boot-update service...${NC}"
sudo systemctl enable --now systemd-boot-update
sleep 3

echo -e "${GREEN}Secure Boot configuration completed!${NC}"
sleep 3
