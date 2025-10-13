#!/usr/bin/bash
# --- INI ---
# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh"
# --- 检查脚本锁 ---
acquire_script_lock || exit 0

# =============================================================================
# CONFIGURATION
# =============================================================================

ICON_ARCH="A:"
ICON_TEMP="T:"
ICON_CPU="C:"
ICON_MEM="M:"
ICON_VOL="V:"
ICON_BT="B:"
ICON_NET_DOWN="D:"
ICON_NET_UP="U:"

CPU_TEMP_FILE="/sys/class/thermal/thermal_zone0/temp"
INTERFACE="enp0s31f6"

UPDATE_INTERVAL_MEDIUM=5
UPDATE_INTERVAL_LONG=60
SEPARATOR="|"

# =============================================================================
# SCRIPT LOGIC
# =============================================================================

kernel_version=$(uname -r)
ARCH="${kernel_version%%-*}"
NET_RX_FILE="/sys/class/net/$INTERFACE/statistics/rx_bytes"
NET_TX_FILE="/sys/class/net/$INTERFACE/statistics/tx_bytes"
if [[ -r "$NET_RX_FILE" ]]; then
	RX1=$(<"$NET_RX_FILE")
	TX1=$(<"$NET_TX_FILE")
else NET_STATUS_STR="N/A"; fi
read -r _ cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_irq cpu_softirq _ </proc/stat
PREV_CPU=$((cpu_user + cpu_nice + cpu_system + cpu_idle + cpu_iowait + cpu_irq + cpu_softirq))
PREV_IDLE=$cpu_idle

CPU_STATUS="" MEM_STATUS="" TEMP_STATUS="" VOL_STATUS=""
MUSIC_STATUS="" IME_STATUS="" TIME_STATUS=""
NET_STATUS_STR=${NET_STATUS_STR:-""}
BLUETOOTH_STATUS=""

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
update_mem() { MEM_STATUS=$(awk '/^MemTotal:/ {t=$2/1024} /^MemAvailable:/ {a=$2/1024} END {printf "%d/%dMB", (t-a), t}' /proc/meminfo); }
update_temp() {
	if [[ -r "$CPU_TEMP_FILE" ]]; then
		local temp_val=$(($(<$CPU_TEMP_FILE) / 1000))
		TEMP_STATUS="${ICON_TEMP}${temp_val}°C"
	else TEMP_STATUS="${ICON_TEMP}N/A"; fi
}
update_bluetooth() {
	BLUETOOTH_STATUS=""
	if ! pgrep -x 'bluetoothd' >/dev/null; then return; fi
	local level
	level=$(bluetoothctl info | grep -m1 'Battery Percentage' | awk -F'[()]' '{print $2}')
	[[ -n "$level" ]] && BLUETOOTH_STATUS="${ICON_BT}${level}%"
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
		MUSIC_STATUS="${music:-Off}"
	else MUSIC_STATUS=""; fi
}
update_ime() { case $(fcitx5-remote 2>/dev/null) in 2) IME_STATUS="CN" ;; *) IME_STATUS="EN" ;; esac }
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
	xsetroot -name "${parts[*]}"
}

trap 'update_volume; print_status_bar' SIGRTMIN+2
trap 'update_ime; print_status_bar' SIGRTMIN+3

update_cpu
update_mem
update_temp
update_music
update_ime
update_time
update_net
update_volume
update_bluetooth

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
