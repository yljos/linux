#!/usr/bin/bash

# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh"
# --- 检查脚本锁 ---
acquire_script_lock || exit 0

SHUTDOWN_FILE="http://10.0.0.21/shutdown"
INTERVAL=300 # 循环间隔秒

while true; do
	# 获取远程文件内容，局域网优化超时
	CONTENT=$(curl -s --connect-timeout 1 --max-time 2 "$SHUTDOWN_FILE")

	# 文件不存在或 curl 失败 → 等待下一轮
	if [ -z "$CONTENT" ]; then
		sleep "$INTERVAL"
		continue
	fi

	# 如果内容为1 → 关机
	if [ "$CONTENT" = "1" ]; then
		notify-send -u critical "检测到关机信号" "系统将在60秒后关机"
		sleep 60

		systemctl poweroff # 测试时注释
		exit 0
	fi # 等待固定间隔再检测
	sleep "$INTERVAL"
done
