#!/usr/bin/bash
# =============================================================================
# Script Lock Library - 脚本锁定库
# =============================================================================
# 提供脚本单例运行功能，防止重复启动同一脚本
# 使用方法：
#   1. 在你的脚本中 source 这个文件
#   2. 调用 acquire_script_lock 函数
#   3. 脚本退出时自动清理锁文件
#
# 示例：
#   #!/usr/bin/bash
#   source /path/to/script_lock.sh
#   acquire_script_lock || exit 0
#   # 你的脚本逻辑...
# =============================================================================

# --- 全局变量 ---
LOCK_DIR="${XDG_RUNTIME_DIR:-/tmp}" # 锁文件目录，优先使用 XDG_RUNTIME_DIR

# --- 函数：获取脚本锁 ---
# 参数：
#   $1 - 可选，自定义锁文件名（不包含路径和扩展名）
# 返回：
#   0 - 成功获取锁
#   1 - 锁已被其他进程持有
acquire_script_lock() {
	# 使用真实文件路径作为锁名，解决软链接问题
	local real_script=$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")
	local lock_name="${1:-$(basename "$real_script" .sh)}"
	local pid_file="${LOCK_DIR}/${lock_name}.pid"

	# 检查是否已存在锁文件
	if [ -f "$pid_file" ]; then
		local old_pid
		old_pid=$(cat "$pid_file" 2>/dev/null)

		# 只验证进程是否仍在运行，不检查进程名（避免软链接问题）
		if [ -n "$old_pid" ] && ps -p "$old_pid" >/dev/null 2>&1; then
			# 进一步验证：检查进程的命令行是否包含相同的脚本路径
			local old_cmdline=$(ps -p "$old_pid" -o args= 2>/dev/null | head -1)
			if echo "$old_cmdline" | grep -q "$(basename "$real_script")"; then
				return 1 # 脚本已在运行
			fi
		fi
	fi

	# 创建新锁文件
	printf "%s\n" "$$" >"$pid_file" || return 1

	# 设置退出时清理锁文件的陷阱
	trap "cleanup_script_lock '$pid_file'" EXIT INT TERM

	return 0
}

# --- 函数：清理脚本锁 ---
cleanup_script_lock() {
	local pid_file="$1"
	[ -f "$pid_file" ] && rm -f "$pid_file"
}
