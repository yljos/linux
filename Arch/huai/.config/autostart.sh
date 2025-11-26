#!/usr/bin/env bash

# --- 配置区域 ---
# 锁文件路径，使用变量更安全
LOCK_SCRIPT="$HOME/.config/script_lock.sh"
SWWW_SCRIPT="$HOME/.config/swww_auto.sh"
SHUTDOWN_SCRIPT="$HOME/.config/shutdown.sh"

# --- 加载脚本锁 ---
if [ -f "$LOCK_SCRIPT" ]; then
    . "$LOCK_SCRIPT"
    acquire_script_lock || exit 0
else
    echo "Warning: Lock script not found." >&2
fi

# --- 工具函数 ---

# 检查进程是否运行
is_running() {
    # -x 精确匹配进程名
    pgrep -x "$1" >/dev/null 2>&1
}

# 异步发送通知 (不再通过 subshell sleep，直接扔给后台)
notify_delayed() {
    local delay=$1
    local title=$2
    local message=$3
    # 使用 nohup 确保主脚本退出后通知依然能发送，且不挂起
    (sleep "$delay" && notify-send "$title" "$message") >/dev/null 2>&1 &
}

# 核心启动逻辑封装
# 用法: start_service "进程名" "启动命令" "通知延迟" "中文描述"
start_service() {
    local proc_name=$1
    local cmd=$2
    local delay=$3
    local desc=$4

    if ! is_running "$proc_name"; then
        # 启动命令 ($cmd 可能包含参数，所以不加引号直接展开，或者使用 eval)
        eval "$cmd" &
        
        # 可选：稍微等待一下以确保进程创建（非阻塞整个脚本的关键，但在 Shell 中很难做到完全无阻塞检测）
        # 这里为了脚本极速执行，我们**去掉** sleep 0.5 的检测。
        # 对于自动启动来说，"火后即焚" (Fire and Forget) 通常体验更好。
        
        # 发送通知
        notify_delayed "$delay" "Autostart" "启动 $desc"
    else
        echo "$desc 已经在运行中"
    fi
}

# --- 主逻辑 ---

# 1. Dunst (通知服务通常最先启动)
start_service "dunst" "dunst" 0 "dunst 通知守护进程"

# 2. 壁纸相关
start_service "swww-daemon" "swww-daemon" 2 "swww-daemon 壁纸守护进程"
# 脚本通常不能用 pgrep -x 匹配，这里直接运行 (假设脚本内部有锁)
sh "$SWWW_SCRIPT" &
notify_delayed 4 "Autostart" "启动 swww_auto.sh 壁纸脚本"

# 3. 关机脚本 (假设脚本内部有锁)
sh "$SHUTDOWN_SCRIPT" &
notify_delayed 6 "Autostart" "启动 shutdown.sh 关机脚本"

# 4. 应用程序
start_service "firefox" "firefox" 8 "Firefox 浏览器"
start_service "Telegram" "Telegram" 10 "Telegram 即时通讯"

# 5. 输入法 (fcitx5 需要 -d 参数)
start_service "fcitx5" "fcitx5 -d" 12 "fcitx5 输入法"

exit 0