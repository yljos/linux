#!/usr/bin/bash
# --- 加载脚本锁库 ---
source "$HOME/.config/script_lock.sh"

# --- 调试信息 ---
echo "脚本启动 PID: $$"
echo "锁文件目录: $LOCK_DIR"
echo "脚本名: $(basename "$0")"
echo "锁文件路径: ${LOCK_DIR}/$(basename "$0" .sh).pid"

# --- 检查脚本锁 ---
if acquire_script_lock; then
    echo "成功获取脚本锁"
else
    echo "脚本已在运行，退出..."
    exit 0
fi

echo "开始主循环..."
while true; do
	/home/huai/.config/swww.sh
	sleep 180
done
