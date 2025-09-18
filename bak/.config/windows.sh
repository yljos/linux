#!/usr/bin/env bash
# 将整个脚本逻辑放入后台执行
(
	# 目标主机信息
	TARGET_HOST="huai-PC"
	MAC_ADDRESS="00:23:24:67:DF:14"
	INTERFACE="enp0s31f6"
	MAX_TRIES=30

	# 检查必要命令是否安装
	for cmd in arping wakeonlan xfreerdp3 notify-send; do
		if ! command -v "$cmd" >/dev/null 2>&1; then
			notify-send "错误" "$cmd 未安装"
			exit 1
		fi
	done

	# 通过主机名获取 IP 地址（仅用于 arping 检测）
	TARGET_IP=$(getent hosts "$TARGET_HOST" | awk '{ print $1 }')
	if [ -z "$TARGET_IP" ]; then
		notify-send "错误" "无法解析主机名"
		exit 1
	fi

	# 连接函数
	connect_to_host() {
		notify-send "连接中" "启动 RDP..." && play ~/.config/dunst/connecting.mp3 >/dev/null 2>&1

		# 启动 RDP 连接并获取进程 ID
		xfreerdp3 /v:"$TARGET_HOST" /u:huai /p:110 /sound /dynamic-resolution /cert:ignore >/dev/null 2>&1 &
		RDP_PID=$!

		# 等待几秒钟检查连接状态
		sleep 5

		# 检查 RDP 进程是否仍在运行
		if kill -0 "$RDP_PID" 2>/dev/null; then
			# 进程仍在运行，可能连接成功
			notify-send "连接成功" "RDP 会话已建立" && play ~/.config/dunst/success.mp3 >/dev/null 2>&1

		else
			# 进程已退出，连接失败
			notify-send "连接失败" "RDP 连接建立失败" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
			exit 1
		fi
	}

	# 检查目标主机是否在线
	if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
		notify-send "已在线" "正在连接..." && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
		connect_to_host
	else
		# 主机离线，尝试唤醒
		notify-send "唤醒中" "发送 WOL 包..." && play ~/.config/dunst/wol.mp3 >/dev/null 2>&1
		if ! wakeonlan "$MAC_ADDRESS" >/dev/null 2>&1; then
			notify-send "唤醒失败" "检查网络连接" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
			exit 1
		fi

		notify-send "等待启动" "检测中..." && play ~/.config/dunst/starting.mp3 >/dev/null 2>&1

		# 等待主机上线
		i=1
		while [ $i -le $MAX_TRIES ]; do
			if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
				notify-send "启动成功" "开始连接" && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
				connect_to_host
				exit 0
			fi

			# 每5秒显示一次进度通知
			if [ $((i % 5)) -eq 0 ]; then
				notify-send "等待中" "$i/$MAX_TRIES 秒"
			fi
			sleep 1
			i=$((i + 1))
		done

		# 超时处理
		notify-send "连接超时" "请检查主机状态" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
		exit 1
	fi
) >/dev/null 2>&1 &
