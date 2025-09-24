#!/usr/bin/bash
# --- INI ---
PID_FILE="${XDG_RUNTIME_DIR}/dwl_status.pid"
SCRIPT_NAME=$(basename "$0")

# --- 检查锁 ---
if [ -f "$PID_FILE" ]; then
	OLD_PID=$(cat "$PID_FILE")
	if ps -p "$OLD_PID" >/dev/null 2>&1 &&
		[ "$(ps -p "$OLD_PID" -o comm=)" = "$SCRIPT_NAME" ]; then
		exit 0
	fi
fi

# --- 创建新锁 ---
printf "%s\n" "$$" >"$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT INT TERM

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================

# --- 1. Icons ---
# (所有模块的显示前缀)
ICON_ARCH="A:"
ICON_TEMP="T:"
ICON_CPU="C:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_BT="B:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"

# --- 2. Colors ---
# (状态栏文本颜色)
C_NORM="^fg(00ff00)"
C_WARN="^fg(ffff00)"
C_CRIT="^fg(ff0000)"
C_RESET="^fg()"

# --- 3. System Settings ---
# (硬件和系统文件路径)
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
INTERFACE="enp0s31f6" # 网卡名称, 使用 `ip a` 命令查看

# --- 4. Behavior Settings ---
# (脚本行为和格式)
UPDATE_INTERVAL_MEDIUM=5 # 中等频率更新间隔(秒), 用于内存/音乐/蓝牙
UPDATE_INTERVAL_LONG=60  # 长时间更新间隔(秒), 用于时钟
SEPARATOR="|"            # 各模块之间的分隔符

# =============================================================================
# --- SCRIPT LOGIC (DO NOT EDIT BELOW THIS LINE) ---
# =============================================================================

# --- 初始化 (Initialization) ---
kernel_version=$(uname -r)
ARCH="${C_NORM}${kernel_version%%-*}${C_RESET}"
NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"
if [[ -r "$NET_RX_FILE" ]]; then
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else NET_STATUS_STR="N/A"; fi
read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
PREV_CPU=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
PREV_IDLE=$cpu_idle

# --- 全局状态变量 ---
CPU_STATUS="" MEM_STATUS="" TEMP_STATUS="" VOL_STATUS=""
MUSIC_STATUS="" IME_STATUS="" TIME_STATUS=""
NET_STATUS_STR=${NET_STATUS_STR:-""}
BLUETOOTH_STATUS=""

# --- 函数定义 (Functions) ---
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
	local color_code="$C_NORM"
	if ((usage >= 90)); then color_code="$C_CRIT"; elif ((usage >= 75)); then color_code="$C_WARN"; fi
	CPU_STATUS="${color_code}$(printf "%02d%%" "$usage")${C_RESET}"
}
update_mem() { MEM_STATUS=$(awk '/^MemTotal:/ {t=$2/1024} /^MemAvailable:/ {a=$2/1024} END {printf "%d/%dMB", (t-a), t}' /proc/meminfo); }
update_temp() {
	if [[ -r "$CPU_TEMP_FILE" ]]; then
		local temp_val=$(($(<$CPU_TEMP_FILE) / 1000))
		local color_code="$C_NORM"
		if ((temp_val >= 80)); then color_code="$C_CRIT"; elif ((temp_val >= 65)); then color_code="$C_WARN"; fi
		TEMP_STATUS="${ICON_TEMP}${color_code}${temp_val}°C${C_RESET}"
	else TEMP_STATUS="${ICON_TEMP}N/A"; fi
}
update_bluetooth() {
	BLUETOOTH_STATUS=""
	if ! pgrep -x 'bluetoothd' >/dev/null; then return; fi

	# 尝试提取电池电量
	local level
	level=$(bluetoothctl info | grep -m1 'Battery Percentage' | awk -F'[()]' '{print $2}')

	# 只有在成功获取电量后才显示信息
	if [ -n "$level" ]; then
		# 根据电量阈值选择颜色
		local color_code="$C_NORM" # 默认使用正常颜色 (绿色)
		if ((level <= 20)); then
			color_code="$C_CRIT" # 电量低于等于 10% 使用严重颜色 (红色)
		elif ((level <= 30)); then
			color_code="$C_WARN" # 电量低于等于 20% 使用警告颜色 (黄色)
		fi

		# 组合最终的显示字符串，格式为 "图标:颜色+电量%+颜色重置"
		BLUETOOTH_STATUS="${ICON_BT}${color_code}${level}%${C_RESET}"
	fi
}
update_volume() {
	local vol
	vol=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | awk -F'/' '/Volume:/ {gsub(/%| /,""); print $2; exit}')
	VOL_STATUS=$(printf "%02d%%" "${vol:-50}")
}
update_music() {
	local mpc_output
	mpc_output=$(mpc)
	if [[ "$mpc_output" == *"[playing]"* ]]; then
		local music_line music
		read -r music_line <<<"$mpc_output"
		music="${music_line##* - }"
		MUSIC_STATUS="${C_NORM}${music:-Off}${C_RESET}"
	else MUSIC_STATUS=""; fi
}
update_ime() { case $(fcitx5-remote 2>/dev/null) in 2) IME_STATUS="${C_WARN}CN${C_RESET}" ;; *) IME_STATUS="${C_NORM}EN${C_RESET}" ;; esac }
update_time() { TIME_STATUS=$(printf "%(%a %b %d %H:%M)T" -1); }
update_net() {
	if [[ -z "$RX1" ]]; then
		NET_STATUS_STR=${NET_STATUS_STR:-"N/A"}
		return
	fi
	local RX2 TX2 RX_DIFF TX_DIFF
	RX2=$(<"$NET_RX_FILE")
	TX2=$(<"$NET_TX_FILE")
	RX_DIFF=$((RX2 - RX1))
	TX_DIFF=$((TX2 - TX1))
	RX1=$RX2
	TX1=$TX2
	NET_STATUS_STR=$(printf "%s%dMbps %s%dMbps" "$ICON_NET_DOWN" "$(((RX_DIFF * 8) / 1000000))" "$ICON_NET_UP" "$(((TX_DIFF * 8) / 1000000))")
}
print_status_bar() {
	local parts=()
	parts+=("${ICON_ARCH}${ARCH}")
	[[ -n "$MUSIC_STATUS" ]] && parts+=("${MUSIC_STATUS}")
	parts+=("${TEMP_STATUS}")
	parts+=("${ICON_CPU}${CPU_STATUS}")
	parts+=("${ICON_MEM}${MEM_STATUS}")
	[[ -n "$BLUETOOTH_STATUS" ]] && parts+=("${BLUETOOTH_STATUS}")
	parts+=("${ICON_VOL}${VOL_STATUS}")
	parts+=("${NET_STATUS_STR}")
	parts+=("${TIME_STATUS}")
	parts+=("${IME_STATUS}")
	local IFS="$SEPARATOR"
	printf "%s\n" "${parts[*]}"
}

# --- 信号陷阱 ---
trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'update_ime; print_status_bar' SIGRTMIN+3

# --- 首次运行 ---
update_cpu
update_mem
update_temp
update_music
update_ime
update_time
update_net
update_volume
update_bluetooth

# --- 主循环 ---
SEC=0
while true; do
	update_cpu
	update_temp
	update_net
	if ! ((SEC % UPDATE_INTERVAL_MEDIUM)); then
		update_mem
		update_music
		update_bluetooth
	fi
	if ! ((SEC % UPDATE_INTERVAL_LONG)); then
		update_time
	fi

	print_status_bar
	sleep 1
	((SEC++))
done
