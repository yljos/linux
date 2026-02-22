#!/usr/bin/env bash

# --- Load script lock library ---
source "$HOME/.config/script_lock.sh" 2>/dev/null
if type acquire_script_lock >/dev/null 2>&1; then
    acquire_script_lock || exit 0
fi

# =============================================================================
# --- Configuration Area ---
# =============================================================================

ICON_TEMP="T:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"
ICON_TIME=""

INTERFACE="enp0s31f6"
# INTERFACE="wlp2s0"
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
MPD_HOST="127.0.0.1"
MPD_PORT="6600"

UPDATE_INTERVAL_MEDIUM=5
UPDATE_INTERVAL_LONG=60
SEPARATOR="|"

# =============================================================================
# --- High-performance Functions ---
# =============================================================================

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

    local rx_kb=$((RX_DIFF / 1024))
    local tx_kb=$((TX_DIFF / 1024))

    NET_STATUS_STR="${ICON_NET_DOWN}${rx_kb}K ${ICON_NET_UP}${tx_kb}K"
}

update_volume() {
    local raw
    VOL_STATUS="50%" 
    raw=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null)
    
    if [[ -n "$raw" ]]; then
        if [[ "$raw" == *"[MUTED]"* ]]; then
            VOL_STATUS="MUTE"
        else
            VOL_STATUS=$(echo "$raw" | awk '{print int($2 * 100) "%"}')
        fi
    fi
}

update_time() { TIME_STATUS=$(printf "%(%a %m.%d %H:%M)T" -1); }

print_status_bar() {
    # Concatenate without IME_STATUS
    local output="${ICON_TEMP}${TEMP_STATUS}${SEPARATOR}${ICON_MEM}${MEM_STATUS}${SEPARATOR}${ICON_VOL}${VOL_STATUS}${SEPARATOR}${NET_STATUS_STR}${SEPARATOR}${ICON_TIME}${TIME_STATUS}"

    # Use Bash native replacement: replace duplicate | with |
    while [[ "$output" == *"${SEPARATOR}${SEPARATOR}"* ]]; do
        output="${output//"${SEPARATOR}${SEPARATOR}"/"${SEPARATOR}"}"
    done

    # Remove leading/trailing separators
    output="${output#"$SEPARATOR"}"
    output="${output%"$SEPARATOR"}"

    xsetroot -name "$output" 
}

# =============================================================================
# --- Main Logic ---
# =============================================================================

NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" ]]; then
    RX1=$(<"$NET_RX_FILE")
    TX1=$(<"$NET_TX_FILE")
else 
    NET_STATUS_STR="N/A"
fi

# Removed SIGRTMIN+3 (IME toggle) trap
trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'exit 0' SIGTERM SIGINT

# --- First Run ---
update_mem
update_temp
update_time
update_net
update_volume

# --- Loop ---
SEC=0
while true; do
    update_temp
    update_net

    if ! ((SEC % UPDATE_INTERVAL_MEDIUM)); then
        update_mem
    fi

    if ! ((SEC % UPDATE_INTERVAL_LONG)); then
        update_time
    fi

    print_status_bar
    sleep 1
    ((SEC++))
done