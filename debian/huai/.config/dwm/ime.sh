#!/usr/bin/env bash
#
# 包装脚本：切换 fcitx5 输入法，并发送信号通知 dwl_status 刷新

# 1. 切换输入法 (您原来的命令)
fcitx5-remote -t

# 2. 发送通知信号
#    确保 PID_FILE 和 SIGNAL_NUM 与 dwl_status.sh 中的设置完全一致
PID_FILE="${XDG_RUNTIME_DIR}/dwm_status.pid"
SIGNAL_NUM=37 # SIGRTMIN+3

if [ -f "$PID_FILE" ]; then
	kill -"$SIGNAL_NUM" "$(cat "$PID_FILE")"
fi
