#!/usr/bin/env bash

# Define color variables
GREEN='\033[0;32m'  # Success messages
YELLOW='\033[1;33m' # Warnings
RED='\033[0;31m'    # Errors
BLUE='\033[0;34m'   # Section titles
CYAN='\033[0;36m'   # Operation details
NC='\033[0m'        # Reset color

echo -e "${BLUE}===== Oh My Zsh Installation Script =====${NC}"
sleep 1

# ==========================================
# Root Privilege Check
# ==========================================
if [ "$(id -u)" -eq 0 ]; then
	SUDO=""
	echo -e "${YELLOW}>> Running as root, sudo will NOT be used for package management${NC}"
else
	# Check if sudo is actually available
	if command -v sudo &>/dev/null; then
		SUDO="sudo"
		echo -e "${YELLOW}>> Running as non-root, sudo WILL be used for package management${NC}"
	else
		echo -e "${RED}>> Error: Running as non-root but 'sudo' command not found.${NC}"
		exit 1
	fi
fi
sleep 1

# ==========================================
# Function: Install Package
# ==========================================
# Minimalist helper to avoid repeating package manager logic
install_package() {
	local PACKAGE_NAME=$1
	if command -v "$PACKAGE_NAME" &>/dev/null; then
		echo -e "${GREEN}>> $PACKAGE_NAME is already installed${NC}"
		return
	fi

	echo -e "${YELLOW}>> Installing $PACKAGE_NAME${NC}"
	if command -v apt &>/dev/null; then
		echo -e "${CYAN}>> Using apt package manager${NC}"
		${SUDO} apt update && ${SUDO} apt install -y "$PACKAGE_NAME"
	elif command -v pacman &>/dev/null; then
		echo -e "${CYAN}>> Using pacman package manager${NC}"
		${SUDO} pacman -S --noconfirm "$PACKAGE_NAME"
	else
		echo -e "${RED}>> Could not detect compatible package manager (apt/pacman). Please install $PACKAGE_NAME manually.${NC}"
		exit 1
	fi
	sleep 1
}

# ==========================================
# Dependency Installation
# ==========================================
# Install zsh, git, and curl (Required for OMZ installer)
install_package "zsh"
install_package "git"
install_package "curl"

# ==========================================
# Shell Configuration
# ==========================================
ZSH_PATH=$(which zsh)

# Ensure zsh is in /etc/shells before changing shell
if ! grep -q "$ZSH_PATH" /etc/shells; then
	echo -e "${YELLOW}>> Adding zsh to /etc/shells${NC}"
	echo "$ZSH_PATH" | ${SUDO} tee -a /etc/shells >/dev/null
fi

# Set zsh as default shell
if [[ "$SHELL" != *"$ZSH_PATH"* ]]; then
	echo -e "${YELLOW}>> Setting zsh as default shell${NC}"
	# Use standard chsh. Note: This may prompt for password.
	chsh -s "$ZSH_PATH"
	echo -e "${GREEN}>> zsh set as default shell${NC}"
else
	echo -e "${GREEN}>> zsh is already set as default shell${NC}"
fi
sleep 1

# ==========================================
# Oh My Zsh Installation
# ==========================================
if [ -d ~/.oh-my-zsh ]; then
	rm -rf ~/.oh-my-zsh/
	echo -e "${YELLOW}>> Re-installing oh-my-zsh${NC}"
else
	echo -e "${YELLOW}>> Installing oh-my-zsh${NC}"
fi

# Run installer (using curl which we just ensured exists)
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended --keep-zshrc
sleep 1

# Minimalist cleanup: remove .git to save space
rm -rf ~/.oh-my-zsh/.git
echo -e "${GREEN}>> oh-my-zsh installation completed${NC}"
sleep 1

# ==========================================
# Theme & Plugins
# ==========================================
ZSH_CUSTOM="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

# Function to install custom plugins/themes
install_zsh_extension() {
	local TYPE=$1 # themes or plugins
	local NAME=$2
	local REPO=$3
	local TARGET_DIR="$ZSH_CUSTOM/$TYPE/$NAME"

	if [ -d "$TARGET_DIR" ]; then
		rm -rf "$TARGET_DIR"
	fi

	echo -e "${YELLOW}>> Installing $NAME $TYPE${NC}"
	git clone --depth 1 "$REPO" "$TARGET_DIR"

	# Minimalist cleanup
	rm -rf "$TARGET_DIR/.git"
	echo -e "${GREEN}>> $NAME installed${NC}"
	sleep 1
}

install_zsh_extension "themes" "powerlevel10k" "https://github.com/romkatv/powerlevel10k.git"
install_zsh_extension "plugins" "zsh-autosuggestions" "https://github.com/zsh-users/zsh-autosuggestions"
install_zsh_extension "plugins" "zsh-syntax-highlighting" "https://github.com/zsh-users/zsh-syntax-highlighting"

# ==========================================
# Configuration (.zshrc)
# ==========================================
echo -e "${BLUE}>> Configuring .zshrc${NC}"
sleep 1

# Set theme
if grep -q 'ZSH_THEME="powerlevel10k/powerlevel10k"' ~/.zshrc; then
	echo -e "${GREEN}>> Theme already set${NC}"
else
	echo -e "${CYAN}>> Setting theme to powerlevel10k${NC}"
	sed -i 's/ZSH_THEME=".*"/ZSH_THEME="powerlevel10k\/powerlevel10k"/' ~/.zshrc
fi

# Configure plugins
if grep -q 'plugins=(git zsh-autosuggestions zsh-syntax-highlighting)' ~/.zshrc; then
	echo -e "${GREEN}>> Plugins already configured${NC}"
else
	echo -e "${CYAN}>> Configuring plugins${NC}"
	sed -i '/^plugins=(git)/c\plugins=(git zsh-autosuggestions zsh-syntax-highlighting)' ~/.zshrc
fi

# Helper to append env vars if missing
append_if_missing() {
	local VAR_NAME=$1
	local CMD=$2
	if grep -q "$VAR_NAME" ~/.zshrc; then
		echo -e "${GREEN}>> $VAR_NAME already set${NC}"
	else
		echo -e "${CYAN}>> Adding $VAR_NAME${NC}"
		echo "$CMD" >>~/.zshrc
	fi
}

echo -e "${BLUE}>> Checking environment variables${NC}"
append_if_missing "export LANG=" "export LANG=en_US.UTF-8"
append_if_missing "export VISUAL=" "export VISUAL=vim"
append_if_missing "export EDITOR=" "export EDITOR=vim"
append_if_missing "export TERM=" "export TERM=xterm-256color"

# Completion message
echo -e "${GREEN}Installation completed! Please restart your terminal or run 'source ~/.zshrc'.${NC}"
sleep 1
echo -e "${BLUE}===== Oh My Zsh Setup Finished =====${NC}"
