#!/usr/bin/env bash

# --- INI ---
PID_FILE="${XDG_RUNTIME_DIR}/dwl_status.pid"

# PID 管理：检查实例是否存在，如果存在则静默退出
if [ -f "$PID_FILE" ] && ps -p "$(cat "$PID_FILE")" >/dev/null 2>&1; then
	exit 0
fi
printf "%s\n" "$$" >"$PID_FILE"
trap 'rm -f "$PID_FILE"' EXIT INT TERM

# --- 配置 (Configuration) ---
ICON_ARCH="󰣇"
ICON_MUSIC="♫"
ICON_TEMP=""
ICON_CPU=""
ICON_MEM="󰍛"
ICON_VOL=""
ICON_NET_DOWN=""
ICON_NET_UP=""
ICON_TIME="󰃰"
# --- 颜色定义 (Color Definitions for Bar Patch) ---
C_NORM="^fg(00ff00)" # 绿色 (正常)
C_WARN="^fg(ffff00)" # 黄色 (警告)
C_CRIT="^fg(ff0000)" # 红色 (严重)
C_RESET="^fg()"      # 重置颜色
# --- 初始化 (Initialization) ---
ARCH="${C_NORM}$(uname -r | cut -d'-' -f1)${C_RESET}"
INTERFACE=enp0s31f6 # 请根据实际情况修改为你的网络接口名称

NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" && -r "$NET_TX_FILE" ]]; then
	# 如果文件可读，说明接口有效，读取初始流量值
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else
	# 任何导致文件不可读的情况（接口名为空、接口不存在等）
	# 都会执行这里
	NET_STATUS_STR="N/A"
fi
# 读取/proc/stat中'cpu'开头的行到各个独立的变量中
read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat

# 计算初始的总CPU时间和空闲时间，并赋值给 prev_cpu 和 prev_idle
prev_cpu=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
prev_idle=$cpu_idle

# --- 全局状态变量 ---
CPU_STATUS="" MEM_STATUS="" TEMP_STATUS="" VOL_STATUS=""
MUSIC_STATUS="" IME_STATUS="" TIME_STATUS=""
NET_STATUS_STR=${NET_STATUS_STR:-""}

# --- 函数定义 (Functions) ---
update_cpu() {
	# 1. 计算CPU使用率 (逻辑不变)
	read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
	local curr_cpu=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
	local curr_idle=$cpu_idle
	total_diff=$((curr_cpu - prev_cpu))
	idle_diff=$((curr_idle - prev_idle))
	if [ "$total_diff" -gt 0 ]; then
		usage=$(((100 * (total_diff - idle_diff)) / total_diff))
	else
		usage=0
	fi
	prev_cpu=$curr_cpu
	prev_idle=$curr_idle
	local usage_str=$(printf "%02d%%" "$usage")

	# 2. 根据使用率决定颜色
	local color_code="$C_NORM" # 默认为正常颜色
	if ((usage >= 90)); then
		color_code="$C_CRIT" # 严重 (>90%)：红色
	elif ((usage >= 75)); then
		color_code="$C_WARN" # 警告 (>75%)：黄色
	fi

	# 3. 组合最终输出
	CPU_STATUS="${color_code}${usage_str}${C_RESET}"
}
update_mem() {
	MEM_STATUS=$(awk '/^MemTotal:/ {t=$2/1024} /^MemAvailable:/ {a=$2/1024} END {printf "%d/%dMB", (t-a), t}' /proc/meminfo)
}
update_temp() {
	local temp_val
	temp_val=$(sensors 2>/dev/null | awk '/Core 0|Package id 0|CPU/ {for(i=1;i<=NF;i++) if($i~/\+[0-9]+\.[0-9]+°C/) {gsub(/\+|°C/,"",$i); print $i; exit}}')

	if [[ -z "$temp_val" ]]; then
		TEMP_STATUS="N/A"
		return
	fi

	local temp_int=${temp_val%.*}

	# 1. 设置默认颜色为“正常”
	local color_code="$C_NORM"

	# 2. 根据温度阈值（65°C 和 80°C）更新颜色
	if ((temp_int >= 80)); then
		color_code="$C_CRIT" # 严重 (>= 80°C)：红色
	elif ((temp_int >= 65)); then
		color_code="$C_WARN" # 警告 (>= 65°C)：黄色
	fi

	# 3. 使用最终的颜色代码组合输出字符串
	TEMP_STATUS="${ICON_TEMP} ${color_code}${temp_int}°C${C_RESET}"
}
update_volume() {
	local vol
	vol=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | awk -F'/' '/Volume:/ {gsub(/%| /,""); print $2; exit}')
	VOL_STATUS=$(printf "%02d%%" "${vol:-50}")
}
update_music() {
    # 使用 awk 判断状态并捕获输出，减少一次 grep
    local status
    status=$(mpc status)
    if [[ "$status" == *"[playing]"* ]]; then
        # 使用 sed 一次性提取艺术家/标题部分，替换 cut | sed
        local music
        music=$(mpc current 2>/dev/null | sed -n 's/.* - //p')
        MUSIC_STATUS="[${music:-Off}]"
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
	local RX2 TX2 RX_DIFF TX_DIFF RX_SPEED TX_SPEED
	RX2=$(<"$NET_RX_FILE")
	TX2=$(<"$NET_TX_FILE")
	RX_DIFF=$((RX2 - RX1))
	TX_DIFF=$((TX2 - TX1))
	RX_SPEED=$(((RX_DIFF * 8) / 1000000))
	TX_SPEED=$(((TX_DIFF * 8) / 1000000))
	RX1=$RX2
	TX1=$TX2
	NET_STATUS_STR=$(printf "%s %dMbps %s %dMbps" "$ICON_NET_DOWN" "$RX_SPEED" "$ICON_NET_UP" "$TX_SPEED")
}

# --- 状态栏打印函数 ---
print_status_bar() {
	# 使用一个数组来存储状态栏的各个模块
	local parts=()

	# 模块1: 内核版本 (始终显示)
	parts+=("${ICON_ARCH} ${ARCH}")

	# 模块2: 音乐 (仅当 MUSIC_STATUS 非空时显示)
	if [[ -n "$MUSIC_STATUS" ]]; then
		parts+=("${ICON_MUSIC} ${MUSIC_STATUS}")
	fi

	# 添加其余模块
	# parts+=("${ICON_TEMP} ${TEMP_STATUS}")
	parts+=("${TEMP_STATUS}")
	parts+=("${ICON_CPU} ${CPU_STATUS}")
	parts+=("${ICON_MEM} ${MEM_STATUS}")
	parts+=("${ICON_VOL} ${VOL_STATUS}")
	parts+=("${NET_STATUS_STR}")
	parts+=("${ICON_TIME} ${TIME_STATUS}")
	parts+=("${IME_STATUS}")

	# 使用 "|" 作为分隔符，将数组中的所有模块连接成一个字符串并打印
	local IFS="|"
	printf "%s\n" "${parts[*]}"
}

# --- 信号陷阱 (Signal Trap) ---
trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'update_ime; print_status_bar' SIGRTMIN+3

# --- 首次运行 ---
# 立即执行所有更新，确保状态栏启动时不是空的
update_cpu
update_mem
update_temp
update_music
update_ime
update_time
update_net
# 首次获取音量，如果音频服务未就绪，将显示默认值 50%
update_volume

# --- 主循环 (Main Loop) ---
sec=0
while true; do
	# 高频更新
	update_cpu
	update_temp
	update_net
	# 中频更新
	if [ $((sec % 5)) -eq 0 ]; then
		update_mem
		update_music
	fi
	# 低频更新
	if [ $((sec % 60)) -eq 0 ]; then
		update_time
	fi

	# 每秒打印一次最新状态
	print_status_bar

	sleep 1
	sec=$((sec + 1))
done
