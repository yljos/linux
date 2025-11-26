#!/usr/bin/env bash

# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh" 2>/dev/null
if type acquire_script_lock >/dev/null 2>&1; then
    acquire_script_lock || exit 0
fi

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================

# --- 1. Icons ---
ICON_ARCH="A:"
ICON_TEMP="T:"
ICON_CPU="C:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_BT="B:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"
ICON_WEATHER="W:"

# --- 2. Colors ---
C_NORM="^fg(00ff00)"
C_WARN="^fg(ffff00)"
C_CRIT="^fg(ff0000)"
C_BLUE="^fg(66a3ff)"
C_RESET="^fg()"

# --- 3. System Settings ---
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
INTERFACE="enp0s31f6"

# [修改点] 直接固定位置 (拼音)
WEATHER_LOCATION="Rongcheng"
# 天气缓存文件
WEATHER_CACHE="/tmp/dwl_weather_status"

# MPD 设置
MPD_HOST="127.0.0.1"
MPD_PORT="6600"

# --- 4. Behavior Settings ---
UPDATE_INTERVAL_MEDIUM=5     # 内存/MPD/蓝牙
UPDATE_INTERVAL_LONG=60      # 时间
UPDATE_INTERVAL_WEATHER=1800 # 天气 (30分钟更新一次)
SEPARATOR="|"

# =============================================================================
# --- HIGH PERFORMANCE FUNCTIONS ---
# =============================================================================

# 1. 异步天气更新 (简化版)
refresh_weather_async() {
    (
        # 直接使用固定位置 Weihai
        # -s: 静默, -m 10: 10秒超时
        raw=$(curl -s -m 10 "wttr.in/${WEATHER_LOCATION}?format=%t+%C")
        
        if [[ -n "$raw" ]]; then
            # 简单的颜色解析逻辑
            temp_str=$(echo "$raw" | grep -oE '[+-]?[0-9]+°?C?')
            cond_str=${raw#"$temp_str"}
            cond_str=${cond_str//+/} 
            
            # 提取数字温度进行颜色判断
            temp_num=$(echo "$temp_str" | grep -oE '[-0-9]+' | head -1)
            color="$C_NORM"
            # 这里的温度阈值可以根据威海的气候微调
            if [[ "$temp_num" -le 10 ]]; then color="$C_BLUE";
            elif [[ "$temp_num" -ge 32 ]]; then color="$C_CRIT";
            elif [[ "$temp_num" -ge 26 ]]; then color="$C_WARN"; fi
            
            # 写入缓存
            echo "${ICON_WEATHER}${color}${temp_str}${C_RESET}${cond_str}" > "$WEATHER_CACHE"
        fi
    ) & 
}

# 2. Pure Bash MPD 客户端 (Socket 直连)
update_music_socket() {
    MUSIC_STATUS=""
    # 尝试打开 TCP 连接 (文件描述符 3)
    if ! exec 3<> /dev/tcp/$MPD_HOST/$MPD_PORT 2>/dev/null; then
        return
    fi

    # 发送命令
    echo -e "currentsong\nstatus\nclose" >&3

    # 读取响应
    local artist="" title="" state="" name=""
    while read -r line <&3; do
        if [[ "$line" == "state: play"* ]]; then state="play"; fi
        if [[ "$line" == "Artist: "* ]]; then artist="${line#Artist: }"; fi
        if [[ "$line" == "Title: "* ]]; then title="${line#Title: }"; fi
        if [[ "$line" == "Name: "* ]]; then name="${line#Name: }"; fi
    done
    exec 3>&- # 关闭连接

    if [[ "$state" == "play" ]]; then
        local display="${title:-$name}"
        [[ -n "$artist" ]] && display="$artist - $title"
        MUSIC_STATUS="${C_NORM}${display:-Unknown}${C_RESET}"
    fi
}

# 3. CPU (/proc 读取)
update_cpu() {
    read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ < /proc/stat
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

# 4. 内存 (Awk)
update_mem() { 
    MEM_STATUS=$(awk '/^MemTotal:/ {t=$2/1024} /^MemAvailable:/ {a=$2/1024} END {printf "%d/%dMB", (t-a), t}' /proc/meminfo)
}

# 5. 温度
update_temp() {
    if [[ -r "$CPU_TEMP_FILE" ]]; then
        local temp_val=$(($(<$CPU_TEMP_FILE) / 1000))
        local color_code="$C_NORM"
        if ((temp_val >= 80)); then color_code="$C_CRIT"; elif ((temp_val >= 65)); then color_code="$C_WARN"; fi
        TEMP_STATUS="${ICON_TEMP}${color_code}${temp_val}°C${C_RESET}"
    else 
        TEMP_STATUS="${ICON_TEMP}N/A"
    fi
}

# 6. 蓝牙
update_bluetooth() {
    BLUETOOTH_STATUS=""
    if ! pgrep -x 'bluetoothd' >/dev/null 2>&1; then return; fi
    local level
    level=$(bluetoothctl info 2>/dev/null | grep -oP 'Battery Percentage: \(\K\d+')
    if [[ -n "$level" ]]; then
        local color_code="$C_NORM"
        if ((level <= 20)); then color_code="$C_CRIT";
        elif ((level <= 30)); then color_code="$C_WARN"; fi
        BLUETOOTH_STATUS="${ICON_BT}${color_code}${level}%${C_RESET}"
    fi
}

# 7. 网络
update_net() {
    if [[ -z "$RX1" ]]; then NET_STATUS_STR=${NET_STATUS_STR:-"N/A"}; return; fi
    local RX2 TX2 RX_DIFF TX_DIFF
    RX2=$(<"$NET_RX_FILE")
    TX2=$(<"$NET_TX_FILE")
    RX_DIFF=$((RX2 - RX1))
    TX_DIFF=$((TX2 - TX1))
    RX1=$RX2
    TX1=$TX2
    NET_STATUS_STR=$(printf "%s%dMbps %s%dMbps" "$ICON_NET_DOWN" "$(((RX_DIFF * 8) / 1000000))" "$ICON_NET_UP" "$(((TX_DIFF * 8) / 1000000))")
}

# 8. 音量
update_volume() {
    local vol
    vol=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | grep -oP '\d+%' | head -1)
    VOL_STATUS="${vol:-50%}"
}

# 9. 输入法
update_ime() { 
    if [[ "$(fcitx5-remote 2>/dev/null)" == "2" ]]; then
        IME_STATUS="${C_WARN}CN${C_RESET}"
    else
        IME_STATUS="${C_NORM}EN${C_RESET}"
    fi
}

update_time() { TIME_STATUS=$(printf "%(%Y-%m-%d %a %H:%M)T" -1); }

print_status_bar() {
    local weather_str=""
    [[ -f "$WEATHER_CACHE" ]] && weather_str=$(<"$WEATHER_CACHE")
    local output="${ICON_ARCH}${ARCH}${SEPARATOR}${MUSIC_STATUS}${SEPARATOR}${TEMP_STATUS}${SEPARATOR}${ICON_CPU}${CPU_STATUS}${SEPARATOR}${ICON_MEM}${MEM_STATUS}"
    [[ -n "$BLUETOOTH_STATUS" ]] && output="${output}${SEPARATOR}${BLUETOOTH_STATUS}"
    output="${output}${SEPARATOR}${ICON_VOL}${VOL_STATUS}${SEPARATOR}${NET_STATUS_STR}"
    [[ -n "$weather_str" ]] && output="${output}${SEPARATOR}${weather_str}"
    output="${output}${SEPARATOR}${TIME_STATUS}${SEPARATOR}${IME_STATUS}"
    output=$(echo "$output" | sed "s/$SEPARATOR$SEPARATOR/$SEPARATOR/g")
    printf "%s\n" "$output"
}

# =============================================================================
# --- MAIN LOGIC ---
# =============================================================================

kernel_version=$(uname -r)
ARCH="${C_NORM}${kernel_version%%-*}${C_RESET}"
NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" ]]; then RX1=$(<"$NET_RX_FILE"); TX1=$(<"$NET_TX_FILE"); else NET_STATUS_STR="N/A"; fi

read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ < /proc/stat
PREV_CPU=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
PREV_IDLE=$cpu_idle

trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'update_ime; print_status_bar' SIGRTMIN+3
trap 'exit 0' SIGTERM SIGINT

# 首次运行
update_cpu; update_mem; update_temp; update_music_socket; update_ime; update_time; update_net; update_volume; update_bluetooth
refresh_weather_async # 首次后台触发

SEC=0
while true; do
    update_cpu
    update_temp
    update_net
    
    if ! ((SEC % UPDATE_INTERVAL_MEDIUM)); then
        update_mem
        update_music_socket
        update_bluetooth
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