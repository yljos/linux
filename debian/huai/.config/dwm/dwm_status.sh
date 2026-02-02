#!/usr/bin/env bash

# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh" 2>/dev/null
if type acquire_script_lock >/dev/null 2>&1; then
	acquire_script_lock || exit 0
fi

# =============================================================================
# --- 配置区域 ---
# =============================================================================

ICON_MUSIC=""
ICON_TEMP="T:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"
ICON_TIME=""

INTERFACE="enp0s31f6"
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
MPD_HOST="127.0.0.1"
MPD_PORT="6600"

UPDATE_INTERVAL_MEDIUM=5
UPDATE_INTERVAL_LONG=60
SEPARATOR="|"

# =============================================================================
# --- 高性能功能函数 ---
# =============================================================================

update_music_socket() {
	# 修改：默认设为空，如果不播放则不占用状态栏空间
	MUSIC_STATUS=""
	if ! exec 3<>/dev/tcp/$MPD_HOST/$MPD_PORT 2>/dev/null; then return; fi
	echo -e "currentsong\nstatus\nclose" >&3
	local artist="" title="" state="" name=""
	while read -r line <&3; do
		if [[ "$line" == "state: play"* ]]; then state="play"; fi
		if [[ "$line" == "Title: "* ]]; then title="${line#Title: }"; fi
		if [[ "$line" == "Name: "* ]]; then name="${line#Name: }"; fi
	done
	exec 3>&-
	if [[ "$state" == "play" ]]; then
		local display="${title:-$name}"
		MUSIC_STATUS="${display:-Unknown}"
	fi
}

update_mem() {
	MEM_STATUS=$(awk '/^MemTotal:/ {t=$2/1024} /^MemAvailable:/ {a=$2/1024} END {printf "%d/%dMB", (t-a), t}' /proc/meminfo)
}

update_temp() {
	if [[ -r "$CPU_TEMP_FILE" ]]; then
		local temp_val=$(($(<$CPU_TEMP_FILE) / 1000))
		TEMP_STATUS="${temp_val}°C"
	else
		TEMP_STATUS="N/A"
	fi
}

update_net() {
	if [[ -z "$RX1" ]]; then
		NET_STATUS_STR="N/A"
		return
	fi

	local RX2 TX2 RX_DIFF TX_DIFF
	# 直接读取 sysfs，避免调用外部进程
	RX2=$(<"$NET_RX_FILE")
	TX2=$(<"$NET_TX_FILE")

	# 计算差值（由于循环是 sleep 1，所以差值即为每秒字节数）
	RX_DIFF=$((RX2 - RX1))
	TX_DIFF=$((TX2 - TX1))

	# 更新旧值供下次计算
	RX1=$RX2
	TX1=$TX2

	# 转换为 KB (字节 / 1024)
	# 使用纯整数运算，性能最高
	local rx_kb=$((RX_DIFF / 1024))
	local tx_kb=$((TX_DIFF / 1024))

	# 格式化输出，保持简洁
	NET_STATUS_STR="${ICON_NET_DOWN}${rx_kb}K ${ICON_NET_UP}${tx_kb}K"
}

update_volume() {
	local raw
	raw=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null)
	# 检查是否包含 [MUTED]
	if [[ "$raw" == *"[MUTED]"* ]]; then
		VOL_STATUS="MUTE"
	else
		# 提取数字部分并转为百分比
		VOL_STATUS=$(echo "$raw" | awk '{print int($2 * 100) "%"}')
	fi
}

update_ime() {
	case $(fcitx5-remote 2>/dev/null) in
	2) IME_STATUS="CN" ;;
	*) IME_STATUS="EN" ;;
	esac
}

update_time() { TIME_STATUS=$(printf "%(%a %m.%d %H:%M)T" -1); }

print_status_bar() {
	local music_part=""
	[[ -n "$MUSIC_STATUS" ]] && music_part="${MUSIC_STATUS}${SEPARATOR}"

	# 先拼接
	local output="${music_part}${ICON_TEMP}${TEMP_STATUS}${SEPARATOR}${ICON_MEM}${MEM_STATUS}${SEPARATOR}${ICON_VOL}${VOL_STATUS}${SEPARATOR}${NET_STATUS_STR}${SEPARATOR}${ICON_TIME}${TIME_STATUS}${SEPARATOR}${IME_STATUS}"

	# 使用 Bash 原生替换：将重复的 || 替换为 |
	while [[ "$output" == *"${SEPARATOR}${SEPARATOR}"* ]]; do
		output="${output//"${SEPARATOR}${SEPARATOR}"/"${SEPARATOR}"}"
	done

	# 移除首尾分隔符
	output="${output#"$SEPARATOR"}"
	output="${output%"$SEPARATOR"}"

	xsetroot -name "$output" 
}

# =============================================================================
# --- 主逻辑 ---
# =============================================================================

NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" ]]; then
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else NET_STATUS_STR="N/A"; fi

trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'update_ime; print_status_bar' SIGRTMIN+3
trap 'exit 0' SIGTERM SIGINT

# --- 首次运行 ---
update_mem
update_temp
update_music_socket
update_ime
update_time
update_net
update_volume

# --- 循环 ---
SEC=0
while true; do
	update_temp
	update_net

	if ! ((SEC % UPDATE_INTERVAL_MEDIUM)); then
		update_mem
		update_music_socket
	fi

	if ! ((SEC % UPDATE_INTERVAL_LONG)); then
		update_time
	fi

	print_status_bar
	sleep 1
	((SEC++))
done
