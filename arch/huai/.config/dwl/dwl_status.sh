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
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
# --- 颜色定义 (Color Definitions for Bar Patch) ---
C_NORM="^fg(00ff00)" # 绿色 (正常)
C_WARN="^fg(ffff00)" # 黄色 (警告)
C_CRIT="^fg(ff0000)" # 红色 (严重)
C_RESET="^fg()"      # 重置颜色
# --- 初始化 (Initialization) ---
kernel_version=$(uname -r)
ARCH="${C_NORM}${kernel_version%%-*}${C_RESET}"
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
    if [[ -r "$CPU_TEMP_FILE" ]]; then
        # 读取的值是毫摄氏度 (e.g., 65000)，需除以1000
        local temp_val=$(($(<$CPU_TEMP_FILE) / 1000))
        local color_code="$C_NORM"

        if ((temp_val >= 80)); then # 使用数字 80
            color_code="$C_CRIT"
        elif ((temp_val >= 65)); then # 使用数字 65
            color_code="$C_WARN"
        fi
        TEMP_STATUS="${ICON_TEMP} ${color_code}${temp_val}°C${C_RESET}"
    else
        TEMP_STATUS="${ICON_TEMP} N/A"
    fi
}
# 获取音量百分比，默认值为 50%（如果无法获取）}
update_volume() {
	local vol
	vol=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | awk -F'/' '/Volume:/ {gsub(/%| /,""); print $2; exit}')
	VOL_STATUS=$(printf "%02d%%" "${vol:-50}")
}
update_music() {
    # 只调用一次 mpc，捕获其所有输出
    local mpc_output
    mpc_output=$(mpc) # mpc 不带参数默认等同于 mpc status

    # 检查输出中是否包含播放状态
    if [[ "$mpc_output" == *"[playing]"* ]]; then
        # 如果在播放，从输出的第一行提取歌曲名
        local music
        music=$(printf "%s" "$mpc_output" | head -n 1 | sed -n 's/.* - //p')
        MUSIC_STATUS="[${music:-Off}]"
    else
        # 如果未播放，则清空状态
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
