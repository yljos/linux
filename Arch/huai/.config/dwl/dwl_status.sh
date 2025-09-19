#!/usr/bin/bash
# --- INI ---
PID_FILE="${XDG_RUNTIME_DIR}/dwl_status.pid"
# 获取脚本自己的名字 (例如 "dwl_status.sh")
SCRIPT_NAME=$(basename "$0")

# --- 检查锁 ---
if [ -f "$PID_FILE" ]; then
	OLD_PID=$(cat "$PID_FILE")
	# 1. 检查旧 PID 是否仍在运行
	# 2. 并且，检查该 PID 对应的进程名是否和当前脚本名一致
	if ps -p "$OLD_PID" >/dev/null 2>&1 &&
		[ "$(ps -p "$OLD_PID" -o comm=)" = "$SCRIPT_NAME" ]; then
		# 如果两个条件都满足，说明锁是有效的，直接退出
		exit 0
	fi
	# 如果代码执行到这里，说明 PID 文件存在，但锁无效 (进程不存在或进程名不匹配)
	# 脚本会继续执行，并用自己的新 PID 覆盖旧文件
fi

# --- 创建新锁 ---
printf "%s\n" "$$" >"$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT INT TERM

# --- 配置 (Configuration) ---
# ICON_ARCH="󰣇"
# ICON_MUSIC="♫"
# ICON_TEMP=""
# ICON_CPU=""
# ICON_MEM="󰍛"
# ICON_VOL=""
# ICON_NET_DOWN=""
# ICON_NET_UP=""
# ICON_TIME="󰃰"
ICON_ARCH="A:"
# ICON_MUSIC="MU:"
ICON_TEMP="T:"
ICON_CPU="C:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"
# ICON_TIME="CL:"
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
INTERFACE="enp0s31f6" # 请根据实际情况修改

# --- 颜色定义 (Color Definitions) ---
C_NORM="^fg(00ff00)"
C_WARN="^fg(ffff00)"
C_CRIT="^fg(ff0000)"
C_RESET="^fg()"

# --- 初始化 (Initialization) ---
kernel_version=$(uname -r)
ARCH="${C_NORM}${kernel_version%%-*}${C_RESET}"
NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" ]]; then
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else
	NET_STATUS_STR="N/A"
fi

read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
prev_cpu=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
prev_idle=$cpu_idle

# --- 全局状态变量 ---
CPU_STATUS="" MEM_STATUS="" TEMP_STATUS="" VOL_STATUS=""
MUSIC_STATUS="" IME_STATUS="" TIME_STATUS=""
NET_STATUS_STR=${NET_STATUS_STR:-""}

# --- 函数定义 (Functions) ---
update_cpu() {
	read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
	local curr_cpu=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
	local curr_idle=$cpu_idle
	local total_diff=$((curr_cpu - prev_cpu))
	local idle_diff=$((curr_idle - prev_idle))
	local usage=0
	if ((total_diff > 0)); then
		usage=$(((100 * (total_diff - idle_diff)) / total_diff))
	fi
	prev_cpu=$curr_cpu
	prev_idle=$curr_idle

	local color_code="$C_NORM"
	if ((usage >= 90)); then
		color_code="$C_CRIT"
	elif ((usage >= 75)); then
		color_code="$C_WARN"
	fi
	CPU_STATUS="${color_code}$(printf "%02d%%" "$usage")${C_RESET}"
}

update_mem() {
	# awk 对于此类任务极为高效，纯 shell 实现反而更慢
	MEM_STATUS=$(awk '/^MemTotal:/ {t=$2/1024} /^MemAvailable:/ {a=$2/1024} END {printf "%d/%dMB", (t-a), t}' /proc/meminfo)
}

update_temp() {
	if [[ -r "$CPU_TEMP_FILE" ]]; then
		local temp_val=$(($(<$CPU_TEMP_FILE) / 1000))
		local color_code="$C_NORM"
		if ((temp_val >= 80)); then
			color_code="$C_CRIT"
		elif ((temp_val >= 65)); then
			color_code="$C_WARN"
		fi
		TEMP_STATUS="${ICON_TEMP}${color_code}${temp_val}°C${C_RESET}"
	else
		TEMP_STATUS="${ICON_TEMP}N/A"
	fi
}

update_volume() {
	# pactl 是数据源，无法移除。awk 已是最高效的处理方式
	local vol
	vol=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | awk -F'/' '/Volume:/ {gsub(/%| /,""); print $2; exit}')
	VOL_STATUS=$(printf "%02d%%" "${vol:-50}")
}

update_music() {
	local mpc_output
	mpc_output=$(mpc)
	if [[ "$mpc_output" == *"[playing]"* ]]; then
		# **优化点**: 使用 read 和参数扩展代替 head 和 sed，实现零进程创建
		local music_line music
		read -r music_line <<<"$mpc_output" # 读取第一行
		music="${music_line##* - }"         # 从变量头部移除最长的 "艺术家 - " 部分
		MUSIC_STATUS="${C_NORM}${music:-Off}${C_RESET}"
	else
		MUSIC_STATUS=""
	fi
}

update_ime() {
	case $(fcitx5-remote 2>/dev/null) in
	2) IME_STATUS="${C_WARN}CN${C_RESET}" ;;
	*) IME_STATUS="${C_NORM}EN${C_RESET}" ;;
	esac
}

update_time() {
	TIME_STATUS=$(printf "%(%a %b %d %H:%M)T" -1)
}

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
	if [[ -n "$MUSIC_STATUS" ]]; then
		parts+=("${MUSIC_STATUS}")
	fi
	parts+=("${TEMP_STATUS}")
	parts+=("${ICON_CPU}${CPU_STATUS}")
	parts+=("${ICON_MEM}${MEM_STATUS}")
	parts+=("${ICON_VOL}${VOL_STATUS}")
	parts+=("${NET_STATUS_STR}")
	parts+=("${TIME_STATUS}")
	parts+=("${IME_STATUS}")
	local IFS="|"
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

# --- 主循环 ---
sec=0
while true; do
	update_cpu
	update_temp
	update_net
	if ! ((sec % 5)); then
		update_mem
		update_music
	fi
	if ! ((sec % 60)); then
		update_time
	fi

	print_status_bar
	sleep 1
	((sec++))
done
