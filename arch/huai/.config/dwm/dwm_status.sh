#!/usr/bin/env bash

# --- Load script lock library ---
source "$HOME/.config/script_lock.sh" 2>/dev/null
if type acquire_script_lock >/dev/null 2>&1; then
	acquire_script_lock || exit 0
fi

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================

ICON_TEMP="T:"
ICON_CPU="C:"
ICON_MEM="M:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"
SEPARATOR="|"

INTERFACE="enp0s31f6"
CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"

UPDATE_INTERVAL_MEDIUM=5
UPDATE_INTERVAL_LONG=60

# --- Mode Auto-Detection ---
# If stdout is a pipe (e.g., ./status.sh | dwl), use stdout. Otherwise, use dwm (xsetroot).
if [[ -p /dev/stdout ]]; then
	WM_MODE="stdout"
else
	WM_MODE="dwm"
fi

# =============================================================================
# --- HIGH PERFORMANCE FUNCTIONS ---
# =============================================================================

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

	local rx_kb=$((RX_DIFF / 1024))
	local tx_kb=$((TX_DIFF / 1024))
	NET_STATUS_STR="${ICON_NET_DOWN}${rx_kb}K ${ICON_NET_UP}${tx_kb}K"
}

update_time() { TIME_STATUS=$(printf "%(%a %Y-%m-%d %H:%M)T" -1); }

print_status_bar() {
	local output="${ICON_TEMP}${TEMP_STATUS}${SEPARATOR}${ICON_CPU}${CPU_STATUS}${SEPARATOR}${ICON_MEM}${MEM_STATUS}${SEPARATOR}${NET_STATUS_STR}${SEPARATOR}${TIME_STATUS}"

	# Clean up duplicate separators
	while [[ "$output" == *"${SEPARATOR}${SEPARATOR}"* ]]; do
		output="${output//"${SEPARATOR}${SEPARATOR}"/"${SEPARATOR}"}"
	done

	# Remove leading/trailing separators
	output="${output#"$SEPARATOR"}"
	output="${output%"$SEPARATOR"}"

	if [[ "$WM_MODE" == "dwm" ]]; then
		xsetroot -name "$output" 2>/dev/null
	else
		printf "%s\n" "$output"
	fi
}

# =============================================================================
# --- MAIN LOGIC ---
# =============================================================================

NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"

if [[ -r "$NET_RX_FILE" ]]; then
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else
	NET_STATUS_STR="N/A"
fi

# Initialize CPU stats
read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
PREV_CPU=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
PREV_IDLE=$cpu_idle

trap 'exit 0' SIGTERM SIGINT

# Initial run
update_cpu
update_mem
update_temp
update_time
update_net

SEC=0
while true; do
	update_cpu
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