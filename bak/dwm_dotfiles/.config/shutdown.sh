#!/usr/bin/env bash

# 监测文件内容是否为1，是则关机，否则5分钟后再检测
SHUTDOWN_FILE="http://nas/shutdown"

while true; do
	# 获取文件内容
	CONTENT=$(curl --silent --connect-timeout 3 --max-time 5 --location --max-redirs 1 "$SHUTDOWN_FILE" 2>/dev/null | tr -d '[:space:]')

	# 检查curl是否成功执行
	if [ $? -ne 0 ]; then
		echo "网络请求失败，5分钟后重试..."
		sleep 300
		continue
	fi

	echo "文件内容: '$CONTENT'"

	# 检查内容是否为1
	if [ "$CONTENT" = "1" ]; then
		echo "检测到关机信号 (内容为1)，准备关机..."
		sudo shutdown now
		exit 0
	else
		echo "未检测到关机信号 (内容: '$CONTENT')，5分钟后重试..."
		sleep 300 # 等待300秒（5分钟）
	fi
done
