#!/bin/bash

# 获取网络接口名称（在循环外执行一次）
INTERFACE=$(ip route | awk '/default/ {print $5; exit}')

# 自动单位转换函数（移到循环外）
get_speed() {
    local bytes=$1
    local mb=$(awk "BEGIN{printf \"%.2f\", $bytes/1048576}")
    echo "${mb}MB/s"
}

# 缓存系统架构信息（移到循环外）
ARCH=$(uname -r | cut -d'-' -f1)

# 缓存文件路径
NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

# 初始化网速计算的变量
NETWORK_ENABLED=false
if [[ -n "$INTERFACE" && -r "$NET_RX_FILE" && -r "$NET_TX_FILE" ]]; then
    RX1=$(< "$NET_RX_FILE")
    TX1=$(< "$NET_TX_FILE")
    NETWORK_ENABLED=true
fi

# 初始化CPU计算
read cpu1 idle1 <<< $(awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5; exit}' /proc/stat)

# dwl 状态输出函数 - 直接输出到 stdout 供 dwl 读取
output_status() {
    local status="$1"
    # dwl bar 补丁会从 stdin 读取状态文本
    printf "%s\n" "$status"
}

# 确保立即输出，无缓冲
exec 1> >(stdbuf -oL cat)

while true; do
    # 实时CPU计算
    read cpu2 idle2 <<< $(awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5; exit}' /proc/stat)
    total=$((cpu2 - cpu1))
    idle=$((idle2 - idle1))
    if (( total > 0 )); then
        usage=$(( (100 * (total - idle)) / total ))
    else
        usage=0
    fi
    cpu=$(printf "%02d%%" "$usage")
    cpu1=$cpu2
    idle1=$idle2
    
    # 系统信息
    mem=$(awk '/^MemTotal:|^MemAvailable:/ {
        if ($1 == "MemTotal:") total = $2/1024
        if ($1 == "MemAvailable:") avail = $2/1024
    } END {printf "%d/%dMB", (total-avail), total}' /proc/meminfo)
    
    temp=$(sensors 2>/dev/null | awk '/Core 0|Package id 0|CPU/ {for(i=1;i<=NF;i++) if($i~/\+[0-9]+\.[0-9]+°C/) {gsub(/\+|°C/,"",$i); printf "%.0f°C",$i; exit}}' || echo "N/A")
    time=$(date "+%a %b %d %H:%M")
    
    # 音频信息
    volume=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | 
             awk '{gsub(/%/, "", $5); printf "%02d%%", $5; exit}')
    
    # 音乐信息
    music=$(mpc current 2>/dev/null | awk -F' - ' '{print $2}')
    music="[${music:-N/A}]"
    
    # 输入法状态
    fcitx5_status=$(fcitx5-remote 2>/dev/null)
    case $fcitx5_status in
        2) fcitx5_display="CN" ;;
        1) fcitx5_display="EN" ;;
        *) fcitx5_display="Er" ;;
    esac

    # 计算网速
    if $NETWORK_ENABLED; then
        RX2=$(< "$NET_RX_FILE")
        TX2=$(< "$NET_TX_FILE")

        RX_DIFF=$((RX2 - RX1))
        TX_DIFF=$((TX2 - TX1))

        RX_SPEED=$(get_speed $RX_DIFF)
        TX_SPEED=$(get_speed $TX_DIFF)

        RX1=$RX2
        TX1=$TX2

        net_speed=" $RX_SPEED  $TX_SPEED"
    else
        net_speed="N/A"
    fi

    # 设置 dwl 状态显示
    status_text="󰣇 $ARCH|♫ $music| $temp| $cpu| $mem| $volume|$net_speed|󰃰 $time|$fcitx5_display"
    output_status "$status_text"
    
    sleep 1
done
