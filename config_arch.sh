#!/usr/bin/env bash

# 定义颜色以便更好地可视化输出
GREEN='\033[0;32m'  # 成功消息
YELLOW='\033[1;33m' # 警告
RED='\033[0;31m'    # 错误
BLUE='\033[0;34m'   # 章节标题
CYAN='\033[0;36m'   # 操作详情
NC='\033[0m'        # 重置颜色

# 错误处理函数
handle_error() {
	echo -e "${RED}Error: $1${NC}"
	echo -e "${YELLOW}Configuration may be incomplete. Check the error and try again.${NC}"
	sleep 5 # 错误消息后等待5秒
}

# 检查命令成功的函数
check_command() {
	if [ $? -ne 0 ]; then
		handle_error "$1"
		return 1
	fi
	return 0
}

# 捕获脚本中断的陷阱
trap 'echo -e "${RED}Script interrupted. Configuration may be incomplete.${NC}"; sleep 5; exit 1' INT TERM

echo -e "${BLUE}===== Starting Arch Linux initial configuration =====${NC}"
sleep 1

# 系统级配置（第一优先级）
echo -e "${BLUE}Setting up system services...${NC}"
echo -e "${CYAN}   Enabling network time synchronization...${NC}"
sudo timedatectl set-ntp true
if ! check_command "Failed to enable network time synchronization"; then
	echo -e "${YELLOW}   Continuing with configuration despite the error...${NC}"
	sleep 3 # 警告消息后等待3秒
fi
echo -e "${GREEN}System services configuration completed.${NC}"
sleep 1 # 成功消息后等待1秒

echo -e "${BLUE}Installing yay AUR ...${NC}"
if command -v yay >/dev/null 2>&1; then
	echo -e "${GREEN}yay is already installed.${NC}"
	sleep 1 # 成功消息后等待1秒
else
	echo -e "${CYAN}   Building and installing yay...${NC}"

	# 检查yay目录是否存在
	if [ ! -d ~/yay ]; then
		echo -e "${CYAN}   Cloning yay repository...${NC}"
		cd ~ && git clone https://aur.archlinux.org/yay.git
		check_command "Failed to clone yay repository"
	fi

	# 进入目录并构建/安装
	if cd ~/yay; then
		makepkg -si --noconfirm
		check_command "Failed to build and install yay"

		# 返回原始目录
		cd ~ || handle_error "Cannot navigate back to home directory"

		echo -e "${GREEN}yay installation completed.${NC}"
		sleep 1 # 成功消息后等待1秒
	else
		handle_error "Cannot navigate to yay directory"
		echo -e "${YELLOW}   Skipping yay installation...${NC}"
		sleep 3
	fi
fi

echo -e "${BLUE}Installing fonts...${NC}"
echo -e "${CYAN}   Creating fonts directory and copying Meslo LG Nerd Font...${NC}"
sudo mkdir -p /usr/local/share/fonts
check_command "Failed to create fonts directory"

if [ -d ~/linux/MesloLGNerdFont ]; then
	sudo cp -r ~/linux/MesloLGNerdFont /usr/local/share/fonts
	check_command "Failed to copy font files"

	fc-cache -fv
	check_command "Failed to update font cache"
	echo -e "${GREEN}Font installation completed.${NC}"
	sleep 1 # 成功消息后等待1秒
else
	echo -e "${YELLOW}   Warning: MesloLGNerdFont directory not found${NC}"
	sleep 3 # 警告消息后等待3秒
fi

echo -e "${BLUE}Setting up numlock...${NC}"
echo -e "${CYAN}   Running numlock configuration script...${NC}"
if [ -d ~/linux/numlock ]; then
	if cd ~/linux/numlock; then
		if [ -f ./numlock.sh ]; then
			bash ./numlock.sh
			check_command "Numlock script encountered an error"
		else
			handle_error "Numlock script not found"
		fi
		# 返回原始目录
		cd ~ || handle_error "Cannot navigate back to home directory"
	else
		handle_error "Cannot navigate to numlock directory"
		echo -e "${YELLOW}   Skipping numlock setup...${NC}"
		sleep 3
	fi
else
	echo -e "${YELLOW}   Warning: numlock directory not found, skipping...${NC}"
	sleep 3 # 警告消息后等待3秒
fi
echo -e "${GREEN}Numlock setup completed.${NC}"
sleep 1 # 成功消息后等待1秒

# 用户配置和环境（中等优先级）
echo -e "${GREEN}Using hyprland window manager.${NC}"

echo -e "${BLUE}Setting up dotfiles with GNU Stow...${NC}"
echo -e "${CYAN}   Using stow to symlink configuration files...${NC}"
if [ -d ~/linux/dotfiles ]; then
	if cd ~/linux; then
		stow dotfiles
		if check_command "Failed to stow dotfiles"; then
			echo -e "${GREEN}Dotfiles stowed successfully.${NC}"
		fi
		cd ~ || handle_error "Cannot navigate back to home directory"
	else
		handle_error "Cannot navigate to ~/linux directory"
		echo -e "${YELLOW}   Skipping dotfiles configuration...${NC}"
		sleep 3
	fi
else
	echo -e "${YELLOW}   Warning: dotfiles directory not found in ~/linux/${NC}"
	echo -e "${YELLOW}   Skipping dotfiles configuration...${NC}"
	sleep 3
fi
sleep 1

echo -e "${BLUE}Setting up user services...${NC}"
echo -e "${CYAN}   Enabling and starting Music Player Daemon (MPD)...${NC}"
systemctl --user enable mpd --now
if ! check_command "Failed to enable/start MPD service"; then
	echo -e "${YELLOW}   MPD service may not be installed or may have failed to start${NC}"
	echo -e "${YELLOW}   Continuing with configuration...${NC}"
	sleep 3 # 警告消息后等待3秒
fi
echo -e "${GREEN}User services configuration completed.${NC}"
sleep 1 # 成功消息后等待1秒

# 工具配置（重要但优先级较低）
echo -e "${BLUE}Configuring SSH...${NC}"
echo -e "${CYAN}   Copying SSH key and setting appropriate permissions...${NC}"
mkdir -p ~/.ssh
check_command "Failed to create ~/.ssh directory"

if [ -f ~/data/linux/.ssh/id_ed25519 ]; then
	cp ~/data/linux/.ssh/id_ed25519 ~/.ssh/
	check_command "Failed to copy SSH key"

	if cd ~/.ssh; then
		chmod 400 id_ed25519
		check_command "Failed to set permissions on SSH key"
		cd ~ || handle_error "Cannot navigate back to home directory"
		echo -e "${GREEN}SSH configuration completed.${NC}"
		sleep 1 # 成功消息后等待1秒
	else
		handle_error "Cannot navigate to ~/.ssh directory"
	fi
else
	echo -e "${YELLOW}   Warning: SSH key not found at ~/data/linux/.ssh/id_ed25519${NC}"
	echo -e "${YELLOW}   SSH configuration incomplete.${NC}"
	sleep 3 # 警告消息后等待3秒
fi

echo -e "${BLUE}Configuring Git settings...${NC}"
echo -e "${CYAN}   Setting Git editor to vim...${NC}"
if command -v git >/dev/null 2>&1; then
	git config --global core.editor "vim" # 设置vim为默认编辑器
	git config --global user.signingkey @outlook.com
	git config --global commit.gpgsign true
	check_command "Failed to set Git editor"

	# 从配置文件读取Git信息
	if [ -f ~/data/linux/github.config ]; then
		# 读取邮箱
		GIT_EMAIL=$(grep "EMAIL=" ~/data/linux/github.config | cut -d= -f2)
		if [ -n "$GIT_EMAIL" ]; then
			git config --global user.email "$GIT_EMAIL"
			check_command "Failed to set Git email"
			echo -e "${CYAN}   Setting Git email from config file...${NC}"
		else
			echo -e "${YELLOW}   Warning: Could not find EMAIL in config file${NC}"
			sleep 3 # 警告消息后等待3秒
		fi

		# 读取用户名
		GIT_USERNAME=$(grep "USERNAME=" ~/data/linux/github.config | cut -d= -f2)
		if [ -n "$GIT_USERNAME" ]; then
			git config --global user.name "$GIT_USERNAME"
			check_command "Failed to set Git username"
			echo -e "${CYAN}   Setting Git username from config file...${NC}"
		else
			echo -e "${YELLOW}   Warning: Could not find USERNAME in config file${NC}"
			sleep 3 # 警告消息后等待3秒
		fi

		# 只有当两个设置都应用时才显示完成消息
		if [ -n "$GIT_EMAIL" ] && [ -n "$GIT_USERNAME" ]; then
			echo -e "${GREEN}Git configuration completed successfully.${NC}"
			sleep 1 # 成功消息后等待1秒
		else
			echo -e "${YELLOW}Git configuration incomplete. Check your config file.${NC}"
			sleep 3 # 警告消息后等待3秒
		fi
	else
		echo -e "${YELLOW}   Warning: Git config file not found at ~/data/linux/github.config${NC}"
		echo -e "${YELLOW}   Skipping Git user configuration.${NC}"
		sleep 3 # 警告消息后等待3秒
	fi
else
	echo -e "${YELLOW}   Warning: Git is not installed, skipping Git configuration...${NC}"
	sleep 3 # 警告消息后等待3秒
fi

# 数据同步（最后一步）
echo -e "${BLUE}Syncing media files from data partition...${NC}"

# 检查数据目录是否存在
if [ ! -d ~/data/Downloads ]; then
	echo -e "${YELLOW}   Warning: ~/data/Downloads directory not found${NC}"
	echo -e "${YELLOW}   Skipping file synchronization...${NC}"
	sleep 3 # 警告消息后等待3秒
else
	echo -e "${CYAN}   Syncing Music directory...${NC}"
	if [ -d ~/data/Downloads/Music ]; then
		mkdir -p ~/Music
		rsync -avzh --delete ~/data/Downloads/Music/ ~/Music
		check_command "Failed to sync Music directory"
	else
		echo -e "${YELLOW}   Warning: Music directory not found in data partition${NC}"
		sleep 3 # 警告消息后等待3秒
	fi

	echo -e "${CYAN}   Syncing Pictures directory...${NC}"
	if [ -d ~/data/Downloads/Pictures ]; then
		mkdir -p ~/Pictures
		rsync -avzh --delete ~/data/Downloads/Pictures/ ~/Pictures
		check_command "Failed to sync Pictures directory"
	else
		echo -e "${YELLOW}   Warning: Pictures directory not found in data partition${NC}"
		sleep 3 # 警告消息后等待3秒
	fi
	echo -e "${GREEN}File synchronization completed.${NC}"
	sleep 1 # 成功消息后等待1秒
fi
sudo systemctl daemon-reload && sudo systemctl enable numlock --now
echo -e "${GREEN}All configurations completed successfully!${NC}"
sleep 1 # 成功消息后等待1秒
echo -e "${BLUE}===== Arch Linux initial configuration completed =====${NC}"
sleep 1 # 最终消息后等待1秒
