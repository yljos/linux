#!/usr/bin/dash
# Configurations
CONFIG_GPG="$HOME/.config/mima.gpg"
TARGET_IP="10.0.0.15"
MAC_ADDRESS="00:23:24:67:DF:14"
INTERFACE="enp0s31f6"
MAX_TRIES=15

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
# 检查依赖
check_dependencies() {
	for cmd in arping wakeonlan notify-send gpg play xfreerdp3; do
		command -v "$cmd" >/dev/null 2>&1 || {
			echo "错误: $cmd 未安装" >&2
			exit 1
		}
	done
}

# 唤醒主机
wake_host() {
	notify-send "唤醒中" "发送 WOL 包..." && play ~/.config/dunst/wol.mp3 >/dev/null 2>&1
	if ! wakeonlan -i 10.0.0.255 "$MAC_ADDRESS" >/dev/null 2>&1; then
		notify-send "唤醒失败" "检查网络连接" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
		exit 1
	fi
	notify-send "等待启动" "检测中..." && play ~/.config/dunst/starting.mp3 >/dev/null 2>&1
}

# 检测主机上线
wait_online() {
	i=1
	while [ $i -le $MAX_TRIES ]; do
		if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
			notify-send "启动成功" "开始连接" && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
			return 0
		fi
		sleep 1
		i=$((i + 1))
	done
	notify-send "连接超时" "请检查主机状态" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
	exit 1
}

# 连接主机
connect_to_host() {
	notify-send "连接中" "启动 RDP..." && play ~/.config/dunst/connecting.mp3 >/dev/null 2>&1
	xfreerdp3 /v:"$TARGET_IP" /u:huai /p:"$PASSWORD" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
}

# 主流程
main() {
	check_dependencies
	if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
		notify-send "已在线" "正在连接..." && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
		connect_to_host
	else
		wake_host
		wait_online && connect_to_host
	fi
}

main &
