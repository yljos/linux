#!/usr/bin/env bash

# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh" 2>/dev/null
if type acquire_script_lock >/dev/null 2>&1; then
	acquire_script_lock || exit 0
fi

# =============================================================================
# --- 配置区域 ---
# =============================================================================

# --- 1. 图标定义 (DWL 文本风格) ---
ICON_ARCH="A:"
ICON_MUSIC=""
ICON_TEMP="T:"
ICON_CPU="C:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"
ICON_TIME=""
ICON_WEATHER="W:"

# --- 2. 系统设置 ---
# 固定网络接口
INTERFACE="enp0s31f6"
# 温度文件
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
# 天气位置
WEATHER_LOCATION="Rongcheng"
WEATHER_CACHE="/tmp/dwm_weather_status"
# MPD 设置
MPD_HOST="127.0.0.1"
MPD_PORT="6600"

# --- 3. 刷新间隔设置 ---
UPDATE_INTERVAL_MEDIUM=5
UPDATE_INTERVAL_LONG=60
UPDATE_INTERVAL_WEATHER=1800
SEPARATOR="|"

# =============================================================================
# --- 高性能功能函数 ---
# =============================================================================

refresh_weather_async() {
	(
		raw=$(curl -s -m 10 "wttr.in/${WEATHER_LOCATION}?format=%t+%C")
		if [[ -n "$raw" ]]; then
			temp_str=$(echo "$raw" | grep -oE '[+-]?[0-9]+°?C?')
			cond_str=${raw#"$temp_str"}
			cond_str=${cond_str//+/}
			echo "${ICON_WEATHER}${temp_str}${cond_str}" >"$WEATHER_CACHE"
		fi
	) &
}

update_music_socket() {
	MUSIC_STATUS="[N/A]"
	if ! exec 3<>/dev/tcp/$MPD_HOST/$MPD_PORT 2>/dev/null; then return; fi
	echo -e "currentsong\nstatus\nclose" >&3
	local artist="" title="" state="" name=""
	while read -r line <&3; do
		if [[ "$line" == "state: play"* ]]; then state="play"; fi
		if [[ "$line" == "Artist: "* ]]; then artist="${line#Artist: }"; fi
		if [[ "$line" == "Title: "* ]]; then title="${line#Title: }"; fi
		if [[ "$line" == "Name: "* ]]; then name="${line#Name: }"; fi
	done
	exec 3>&-
	if [[ "$state" == "play" ]]; then
		local display="${title:-$name}"
		[[ -n "$artist" ]] && display="$artist - $display"
		MUSIC_STATUS="[${display:-Unknown}]"
	fi
}

update_cpu() {
	read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
	local curr_cpu=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
	local curr_idle=$cpu_idle
	local total_diff=$((curr_cpu - PREV_CPU))
	local idle_diff=$((curr_idle - PREV_IDLE))
	local usage=0
	if ((total_diff > 0)); then usage=$(((100 * (total_diff - idle_diff)) / total_diff)); fi
	PREV_CPU=$curr_cpu
	PREV_IDLE=$curr_idle
	CPU_STATUS="$(printf "%02d%%" "$usage")"
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
	RX2=$(<"$NET_RX_FILE")
	TX2=$(<"$NET_TX_FILE")
	RX_DIFF=$((RX2 - RX1))
	TX_DIFF=$((TX2 - TX1))
	RX1=$RX2
	TX1=$TX2
	local rx_mbps=$(((RX_DIFF * 8) / 1000000))
	local tx_mbps=$(((TX_DIFF * 8) / 1000000))
	NET_STATUS_STR="${ICON_NET_DOWN}${rx_mbps}Mbps ${ICON_NET_UP}${tx_mbps}Mbps"
}

update_volume() {
	local vol
	vol=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | grep -oP '\d+%' | head -1)
	VOL_STATUS="${vol:-0%}"
}

update_ime() {
	# 修复了此处的语法错误
	case $(fcitx5-remote 2>/dev/null) in
	2) IME_STATUS="CN" ;;
	1) IME_STATUS="EN" ;;
	*) IME_STATUS="Er" ;;
	esac
}

update_time() { TIME_STATUS=$(printf "%(%a %b %d %H:%M)T" -1); }

print_status_bar() {
	local weather_str=""
	[[ -f "$WEATHER_CACHE" ]] && weather_str=$(<"$WEATHER_CACHE")

	local output="${ICON_ARCH}${ARCH}${SEPARATOR}${ICON_MUSIC}${MUSIC_STATUS}${SEPARATOR}${ICON_TEMP}${TEMP_STATUS}${SEPARATOR}${ICON_CPU}${CPU_STATUS}${SEPARATOR}${ICON_MEM}${MEM_STATUS}${SEPARATOR}${ICON_VOL}${VOL_STATUS}${SEPARATOR}${NET_STATUS_STR}"
	[[ -n "$weather_str" ]] && output="${output}${SEPARATOR}${weather_str}"
	output="${output}${SEPARATOR}${ICON_TIME}${TIME_STATUS}${SEPARATOR}${IME_STATUS}"

	output=$(echo "$output" | sed "s/$SEPARATOR$SEPARATOR/$SEPARATOR/g")

	# 强制使用 xsetroot 设置 DWM 状态
	xsetroot -name "$output"
}

# =============================================================================
# --- 主逻辑 ---
# =============================================================================

ARCH=$(uname -r | cut -d'-' -f1)
NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" ]]; then
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else NET_STATUS_STR="N/A"; fi

read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
PREV_CPU=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
PREV_IDLE=$cpu_idle

trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'update_ime; print_status_bar' SIGRTMIN+3
trap 'exit 0' SIGTERM SIGINT

# --- 首次运行 ---
update_cpu
update_mem
update_temp
update_music_socket
update_ime
update_time
update_net
update_volume
refresh_weather_async

# --- 循环 ---
SEC=0
while true; do
	update_cpu
	update_temp
	update_net

	if ! ((SEC % UPDATE_INTERVAL_MEDIUM)); then
		update_mem
		update_music_socket
	fi

	if ! ((SEC % UPDATE_INTERVAL_LONG)); then
		update_time
	fi

	if ! ((SEC % UPDATE_INTERVAL_WEATHER)); then
		refresh_weather_async
	fi

	print_status_bar
	sleep 1
	((SEC++))
done
