#!/usr/bin/env bash

# --- 1. 加载脚本锁 (保持原有逻辑) ---
LOCK_FILE="$HOME/.config/script_lock.sh"
if [ -f "$LOCK_FILE" ]; then
	. "$LOCK_FILE"
	acquire_script_lock || exit 0
fi

# --- 2. 核心函数: 启动并静默检查 ---
# 用法: run_silent "匹配模式(pgrep用)" "启动命令" "中文名称"
run_silent() {
	local match_pattern="$1"
	local run_cmd="$2"
	local app_name="$3"

	# A. 启动前检查：如果已经在运行，直接跳过，啥也不干
	# 使用 -f 模糊匹配，既能匹配 "dunst"，也能匹配 "sh script.sh"
	if pgrep -f "$match_pattern" >/dev/null 2>&1; then
		return 0
	fi

	# B. 启动进程 (丢弃输出，后台运行)
	# 使用 eval 确保带参数的命令(如 fcitx5 -d)能正确执行
	eval "$run_cmd" >/dev/null 2>&1 &

	# C. 异步延时检查 (关键优化)
	# 将"等待3秒后检查"这个动作也放入后台，主脚本不阻塞
	(
		sleep 3
		# 3秒后再次检查，如果找不到进程，说明启动失败
		if ! pgrep -f "$match_pattern" >/dev/null 2>&1; then
			notify-send -u critical "启动失败" "❌ 无法启动: $app_name"
		fi
	) &
}

# --- 3. 任务列表 ---

# Dunst (通知服务)
# 注意: dunst 必须先活下来，否则后面的 notify-send 发不出去
# 这里为了保险，我们可以稍微特殊处理，不放后台等待，确保它起来
# if ! pgrep -x "dunst" >/dev/null; then
# 	dunst &
# 	sleep 0.5 # 稍微给点面子等待一下
# fi
# mako
killall mako >/dev/null 2>&1
mako &
sleep 0.5 # 稍微给点面子等待一下
# 壁纸守护进程 (修正版)
# 1. 强制清理可能导致 Firejail 崩溃的非法双点号文件
rm -f /run/user/$(id -u)/wayland-0-swww-daemon..sock >/dev/null 2>&1

# 2. 确保启动环境有变量支撑，防止再次生成非法文件名
# 如果你是用的是默认的 wayland-0，可以直接 export
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}

run_silent "swww-daemon" "swww-daemon -n 0" "swww 守护进程"

# 壁纸自动切换脚本 (匹配完整路径)
SWWW_SCRIPT="$HOME/.config/swww_auto.sh"
run_silent "$SWWW_SCRIPT" "sh $SWWW_SCRIPT" "swww_auto.sh"

# 关机脚本
SHUTDOWN_SCRIPT="$HOME/.config/shutdown.sh"
run_silent "$SHUTDOWN_SCRIPT" "sh $SHUTDOWN_SCRIPT" "shutdown.sh"

# Firefox
run_silent "firefox" "firefox" "Firefox 浏览器"

# Telegram
run_silent "Telegram" "Telegram" "Telegram"

# Fcitx5 输入法
run_silent "fcitx5" "fcitx5 -d" "Fcitx5 输入法"

exit 0
