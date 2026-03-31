#!/usr/bin/env bash

GAME_PROCESS="Stardew Valley"
MAX_PLAY_TIME=$((120 * 60))   # 120 分钟（以秒为单位）
WARNING_TIME=$((60 * 60))     # 60 分钟（以秒为单位）
MID_WARNING_TIME=$((30 * 60)) # 30 分钟（以秒为单位）
DATA_DIR="$HOME/.game_timer"
TODAY=$(date +%Y-%m-%d)

# 初始化数据目录和文件
init_data_dir() {
	if [ ! -d "$DATA_DIR" ]; then
		mkdir -p "$DATA_DIR" || {
			echo "错误：无法创建数据目录 $DATA_DIR" >&2
			exit 1
		}
		# 设置目录权限
		chmod 700 "$DATA_DIR"
	fi

	# 确保今日数据文件存在
	local time_file="$DATA_DIR/$TODAY"
	if [ ! -f "$time_file" ]; then
		echo "0" >"$time_file" || {
			echo "错误：无法创建时间记录文件 $time_file" >&2
			exit 1
		}
		chmod 600 "$time_file"
	fi
}

# 在脚本开始时调用初始化函数
init_data_dir

# 获取今日累计游戏时间
get_daily_time() {
	local time_file="$DATA_DIR/$TODAY"
	if [ -f "$time_file" ]; then
		cat "$time_file"
	else
		echo "0"
	fi
}

# 更新今日累计游戏时间
update_daily_time() {
	local session_time=$1
	local time_file="$DATA_DIR/$TODAY"
	local current_total=$(get_daily_time)
	local new_total=$((current_total + session_time))
	echo "$new_total" >"$time_file"
	echo "$new_total" # 打印新的总时间而不是使用return
}

check_game() {
	ps aux | grep -i "[S]tardew Valley" >/dev/null
	return $?
}

handle_game_exit() {
	local session_time=$1
	local total_time=$2
	local s_hours=$((session_time / 3600))
	local s_minutes=$(((session_time % 3600) / 60))
	local t_hours=$((total_time / 3600))
	local t_minutes=$(((total_time % 3600) / 60))
	notify-send "星露谷物语" "本次游戏: ${s_hours}小时${s_minutes}分钟\n今日总计: ${t_hours}小时${t_minutes}分钟"
}

while true; do
	# 检查是否需要重置（新的一天）
	CURRENT_DATE=$(date +%Y-%m-%d)
	if [ "$CURRENT_DATE" != "$TODAY" ]; then
		TODAY=$CURRENT_DATE
	fi

	if check_game; then
		START_TIME=$(date +%s)
		DAILY_TIME=$(get_daily_time)
		notify-send -u normal "星露谷物语" "检测到游戏启动！\n今日已玩: $((DAILY_TIME / 60))分钟"

		GAME_EXITED=false
		while [ "$GAME_EXITED" = false ]; do
			CURRENT_TIME=$(date +%s)
			SESSION_TIME=$((CURRENT_TIME - START_TIME))
			TOTAL_TIME=$((DAILY_TIME + SESSION_TIME))

			if [ $TOTAL_TIME -ge $MAX_PLAY_TIME ]; then
				notify-send -u critical "星露谷物语" "今日游戏时间已达上限，你还有 1 分钟来保存，游戏将强制退出！" && play ~/.config/dunst/max_warn.mp3
				sleep 60
				if check_game; then
					pkill -f "[S]tardew Valley"
				fi
				GAME_EXITED=true
			elif [ $TOTAL_TIME -ge $WARNING_TIME ] && [ $TOTAL_TIME -lt $((WARNING_TIME + 30)) ] && [ $((TOTAL_TIME - SESSION_TIME)) -lt $WARNING_TIME ]; then
				notify-send -u normal "星露谷物语" "今日游戏时间已达 1 小时，请注意休息！" && play ~/.config/dunst/60_warn.mp3
			elif [ $TOTAL_TIME -ge $MID_WARNING_TIME ] && [ $TOTAL_TIME -lt $((MID_WARNING_TIME + 30)) ] && [ $((TOTAL_TIME - SESSION_TIME)) -lt $MID_WARNING_TIME ]; then
				notify-send -u normal "星露谷物语" "今日游戏时间已达 30 分钟！" && play ~/.config/dunst/30_warn.mp3
			fi

			if ! check_game; then
				GAME_EXITED=true
			fi

			[ "$GAME_EXITED" = false ] && sleep 30
		done

		# 游戏退出后的处理
		TOTAL_TIME=$(update_daily_time $SESSION_TIME)
		handle_game_exit $SESSION_TIME $TOTAL_TIME
	fi
	sleep 30
done
