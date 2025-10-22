#!/usr/bin/dash
# Configurations
CONFIG_GPG="$HOME/.config/mima.gpg"
TARGET_IP="192.168.31.15"
MAC_ADDRESS="00:23:24:67:DF:14"
INTERFACE="enp0s31f6"
MAX_TRIES=10
# Decrypt password
if [ ! -f "$CONFIG_GPG" ]; then
	notify-send "脚本错误" "找不到 $CONFIG_GPG"
	exit 1
fi
if ! PASSWORD=$(gpg -d "$CONFIG_GPG" 2>/dev/null); then
	notify-send "脚本错误" "解密 $CONFIG_GPG 失败。"
	exit 1
fi
PASSWORD=$(printf "%s" "$PASSWORD")
# check dependencies
for cmd in arping wakeonlan notify-send gpg play xfreerdp3; do
	if ! command -v "$cmd" >/dev/null 2>&1; then
		if command -v notify-send >/dev/null 2>&1; then
			notify-send "错误" "$cmd 未安装"
		else
			echo "错误: $cmd 未安装" >&2
		fi
		exit 1
	fi
done
(
	# Function to connect to the host
	connect_to_host() {
		notify-send "连接中" "启动 RDP..." && play ~/.config/dunst/connecting.mp3 >/dev/null 2>&1
	env SDL_VIDEODRIVER=wayland sdl-freerdp3 /v:192.168.31.15 /u:huai /p:"$PASSWORD" /cert:ignore /sound /w:1916 /h:1056 &

	}
	# check if the host is online
	if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
		notify-send "已在线" "正在连接..." && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
		connect_to_host
	else
		notify-send "唤醒中" "发送 WOL 包..." && play ~/.config/dunst/wol.mp3 >/dev/null 2>&1
		if ! wakeonlan -i 192.168.31.255 "$MAC_ADDRESS" >/dev/null 2>&1; then
			notify-send "唤醒失败" "检查网络连接" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
			exit 1
		fi
		notify-send "等待启动" "检测中..." && play ~/.config/dunst/starting.mp3 >/dev/null 2>&1
		i=1
		while [ $i -le $MAX_TRIES ]; do
			if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
				notify-send "启动成功" "开始连接" && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
				connect_to_host
				exit 0
			fi
			if [ $((i % 2)) -eq 0 ]; then
				notify-send "等待中" "$i/$MAX_TRIES 秒"
			fi
			sleep 1
			i=$((i + 1))
		done
		notify-send "连接超时" "请检查主机状态" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
		exit 1
	fi
) >/dev/null 2>&1 &
