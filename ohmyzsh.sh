#!/bin/bash

# Define color variables
GREEN='\033[0;32m'    # Success messages
YELLOW='\033[1;33m'   # Warnings
RED='\033[0;31m'      # Errors
BLUE='\033[0;34m'     # Section titles
CYAN='\033[0;36m'     # Operation details
NC='\033[0m'          # Reset color

echo -e "${BLUE}===== Oh My Zsh Installation Script =====${NC}"
sleep 3

# Check if zsh is installed
if command -v zsh &>/dev/null; then
    echo -e "${GREEN}>> zsh is already installed, skipping installation${NC}"
    sleep 3
else
    echo -e "${YELLOW}>> Installing zsh${NC}"
    # Detect package manager and install zsh
    if command -v apt &>/dev/null; then
        # Debian, Ubuntu, etc.
        echo -e "${CYAN}>> Using apt package manager${NC}"
        sudo apt update && sudo apt install -y zsh
        sleep 3
    elif command -v pacman &>/dev/null; then
        # Arch Linux
        echo -e "${CYAN}>> Using pacman package manager${NC}"
        sudo pacman -S --noconfirm zsh
        sleep 3
    else
        echo -e "${RED}>> Could not detect compatible package manager. Please install zsh manually.${NC}"
        sleep 3
        exit 1
    fi
fi

# Set zsh as default shell if it's not already
if [[ "$SHELL" != *"zsh"* ]]; then
    echo -e "${YELLOW}>> Setting zsh as default shell${NC}"
    chsh -s $(which zsh)
    sleep 3
else
    echo -e "${GREEN}>> zsh is already set as default shell${NC}"
    sleep 3
fi

# Install oh-my-zsh
if [ -d ~/.oh-my-zsh ]; then
    echo -e "${GREEN}>> oh-my-zsh is already installed, skipping installation${NC}"
    sleep 3
else
    echo -e "${YELLOW}>> Installing oh-my-zsh${NC}"
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended --keep-zshrc
    sleep 3
fi

# Install powerlevel10k theme
if [ -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/themes/powerlevel10k ]; then
    echo -e "${GREEN}>> powerlevel10k theme is already installed, skipping installation${NC}"
    sleep 3
else
    echo -e "${YELLOW}>> Installing powerlevel10k theme${NC}"
    git clone https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/themes/powerlevel10k
    sleep 3
fi

# Install zsh-autosuggestions plugin
if [ -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions ]; then
    echo -e "${GREEN}>> zsh-autosuggestions plugin is already installed, skipping installation${NC}"
    sleep 3
else
    echo -e "${YELLOW}>> Installing zsh-autosuggestions plugin${NC}"
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
    sleep 3
fi

# Install zsh-syntax-highlighting plugin
if [ -d ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting ]; then
    echo -e "${GREEN}>> zsh-syntax-highlighting plugin is already installed, skipping installation${NC}"
    sleep 3
else
    echo -e "${YELLOW}>> Installing zsh-syntax-highlighting plugin${NC}"
    git clone https://github.com/zsh-users/zsh-syntax-highlighting ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
    sleep 3
fi

# Configure oh-my-zsh
echo -e "${BLUE}>> Configuring oh-my-zsh${NC}"
sleep 3

# Set theme to powerlevel10k (only if not already set)
if grep -q 'ZSH_THEME="powerlevel10k/powerlevel10k"' ~/.zshrc; then
    echo -e "${GREEN}>> Theme already set to powerlevel10k, skipping configuration${NC}"
    sleep 3
else
    echo -e "${CYAN}>> Setting theme to powerlevel10k${NC}"
    sed -i 's/ZSH_THEME=".*"/ZSH_THEME="powerlevel10k\/powerlevel10k"/' ~/.zshrc
    sleep 3
fi

# Add plugins to .zshrc (only if not already added)
if grep -q 'plugins=(git zsh-autosuggestions zsh-syntax-highlighting)' ~/.zshrc; then
    echo -e "${GREEN}>> Plugins already configured, skipping configuration${NC}"
    sleep 3
else
    echo -e "${CYAN}>> Configuring plugins${NC}"
    sed -i '/plugins=(git)/c\plugins=(git zsh-autosuggestions zsh-syntax-highlighting)' ~/.zshrc
    sleep 3
fi

# Add environment variables to .zshrc (only if not already added)
echo -e "${BLUE}>> Checking and adding environment variables${NC}"
sleep 3

# Add LANG environment variable
if grep -q 'export LANG=en_US.UTF-8' ~/.zshrc; then
    echo -e "${GREEN}>> LANG environment variable already set, skipping${NC}"
    sleep 3
else
    echo -e "${CYAN}>> Adding LANG environment variable${NC}"
    echo 'export LANG=en_US.UTF-8' >> ~/.zshrc
    sleep 3
fi

# Add VISUAL environment variable
if grep -q 'export VISUAL=vim' ~/.zshrc; then
    echo -e "${GREEN}>> VISUAL environment variable already set, skipping${NC}"
    sleep 3
else
    echo -e "${CYAN}>> Adding VISUAL environment variable${NC}"
    echo 'export VISUAL=vim' >> ~/.zshrc
    sleep 3
fi

# Add EDITOR environment variable
if grep -q 'export EDITOR=vim' ~/.zshrc; then
    echo -e "${GREEN}>> EDITOR environment variable already set, skipping${NC}"
    sleep 3
else
    echo -e "${CYAN}>> Adding EDITOR environment variable${NC}"
    echo 'export EDITOR=vim' >> ~/.zshrc
    sleep 3
fi

# Add TERM environment variable
if grep -q 'export TERM=xterm-256color' ~/.zshrc; then
    echo -e "${GREEN}>> TERM environment variable already set, skipping${NC}"
    sleep 3
else
    echo -e "${CYAN}>> Adding TERM environment variable${NC}"
    echo 'export TERM=xterm-256color' >> ~/.zshrc
    sleep 3
fi

# Completion message
echo -e "${GREEN}Installation completed! Please restart your terminal or run 'source ~/.zshrc' to apply changes.${NC}"
sleep 3
echo -e "${BLUE}===== Oh My Zsh Setup Finished =====${NC}"
sleep 3

