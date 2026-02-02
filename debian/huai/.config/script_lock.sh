#!/usr/bin/bash

# =============================================================================
# 优化版：基于文件描述符的原子锁
# =============================================================================

acquire_script_lock() {
	local lock_name="${1:-$(basename "$0" .sh)}"
	local lock_file="${XDG_RUNTIME_DIR:-/tmp}/${lock_name}.lock"

	# 打开文件描述符 200 (一个不常用的数字) 指向锁文件
	exec 200>"$lock_file"

	# 尝试获取排他锁 (non-blocking)
	# flock -n 成功返回 0，失败返回 1
	if ! flock -n 200; then
		echo "Script is already running." >&2
		return 1
	fi

	# 锁获取成功后，文件描述符会一直保持打开状态直到进程退出
	return 0
}
