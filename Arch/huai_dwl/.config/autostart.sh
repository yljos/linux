#!/usr/bin/bash

# --- 加载脚本锁库 ---
. "$HOME/.config/script_lock.sh"
# --- 检查脚本锁 ---
acquire_script_lock || exit 0

# Function to check if a process is running
is_running() {
	pgrep -x "$1" >/dev/null 2>&1
}

# Function to send delayed notification asynchronously
notify_delayed() {
	local delay=$1
	local title=$2
	local message=$3
	(sleep "$delay" && notify-send "$title" "$message") &
}

# Start dunst if not running
if ! is_running "dunst"; then
	dunst &
	sleep 0.5
	if is_running "dunst"; then
		notify_delayed 0 "Autostart" "启动 dunst 通知守护进程"
	fi
fi

# Start swww-daemon if not running
if ! is_running "swww-daemon"; then
	swww-daemon &
	sleep 0.5
	if is_running "swww-daemon"; then
		notify_delayed 2 "Autostart" "启动 swww-daemon 壁纸守护进程"
	fi
fi

# Start swww_auto.sh script (has built-in script lock)
sh /home/huai/.config/swww_auto.sh &
notify_delayed 4 "Autostart" "启动 swww_auto.sh 壁纸脚本"

# Start shutdown.sh script (has built-in script lock)
sh /home/huai/.config/shutdown.sh &
notify_delayed 6 "Autostart" "启动 shutdown.sh 关机脚本"

# Start firefox if not running
if ! is_running "firefox"; then
	firefox &
	sleep 0.5
	if is_running "firefox"; then
		notify_delayed 8 "Autostart" "启动 Firefox 浏览器"
	fi
fi

# Start Telegram if not running (check for Telegram process)
if ! is_running "Telegram"; then
	Telegram &
	sleep 0.5
	if is_running "Telegram"; then
		notify_delayed 10 "Autostart" "启动 Telegram 即时通讯"
	fi
fi

# Start fcitx5 if not running
if ! is_running "fcitx5"; then
	fcitx5 -d
	sleep 0.5
	if is_running "fcitx5"; then
		notify_delayed 12 "Autostart" "启动 fcitx5 输入法"
	fi
fi
