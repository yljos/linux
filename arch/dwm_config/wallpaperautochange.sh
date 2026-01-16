#!/usr/bin/env bash
# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh"
# --- 检查脚本锁 ---
acquire_script_lock || exit 0

while true; do
	/bin/bash /home/huai/.config/wallpaperchange.sh
	sleep 1m
done
