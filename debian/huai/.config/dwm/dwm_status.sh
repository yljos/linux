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
        MUSIC_STATUS="[${display:-Unknown}]"
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
    case $(fcitx5-remote 2>/dev/null) in
    2) IME_STATUS="CN" ;;
    *) IME_STATUS="EN" ;;
    esac
}

update_time() { TIME_STATUS=$(printf "%(%a %b %d %H:%M)T" -1); }

print_status_bar() {
    # 动态组装：如果 MUSIC_STATUS 为空，这里会产生一个前导分隔符
    local music_part=""
    [[ -n "$MUSIC_STATUS" ]] && music_part="${ICON_MUSIC}${MUSIC_STATUS}${SEPARATOR}"

    local output="${music_part}${ICON_TEMP}${TEMP_STATUS}${SEPARATOR}${ICON_MEM}${MEM_STATUS}${SEPARATOR}${ICON_VOL}${VOL_STATUS}${SEPARATOR}${NET_STATUS_STR}${SEPARATOR}${ICON_TIME}${TIME_STATUS}${SEPARATOR}${IME_STATUS}"

    # 1. 处理重复的分隔符 (如果有模块为空)
    output=$(echo "$output" | sed "s/$SEPARATOR$SEPARATOR/$SEPARATOR/g")
    # 2. 移除行首和行尾可能存在的分隔符
    output=${output#$SEPARATOR}
    output=${output%$SEPARATOR}

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