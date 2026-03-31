#!/usr/bin/bash
# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh"
# --- 检查脚本锁 ---
acquire_script_lock || exit 0

while true; do
	/home/huai/.config/swww.sh
	sleep 180
done
