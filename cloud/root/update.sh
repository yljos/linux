#!/bin/bash

# === 配置区域 ===
BASE_DIR="/root/linux/free"
SERVICES="convert" # 如果以后有多个，用空格隔开: "convert web"
LOCK_FILE="/tmp/update.sh.lock"

# === 环境与函数 ===
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/libexec/podman:/usr/lib/podman

log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# === 1. 并发锁 (防堆积) ===
exec 9>"$LOCK_FILE" || exit 1
flock -n 9 || {
	log "已有实例在运行，退出。"
	exit 0
}

log "脚本启动: 检查远程更新..."

# === 2. 极简更新检测 ===
cd "$BASE_DIR" || {
	log "错误: 无法进入目录 $BASE_DIR"
	exit 1
}

# 仅获取元数据
git fetch --quiet origin

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse @{u})

if [ "$LOCAL_HASH" == "$REMOTE_HASH" ]; then
	# 极简主义核心：无更新直接退出，零资源消耗
	# 注意：这里 exit 0 是安全的，因为没有更新就不需要构建
	exit 0
fi

log "检测到远程更新: ${LOCAL_HASH:0:7} -> ${REMOTE_HASH:0:7}"

if ! git merge --ff-only --quiet; then
	log "错误: 无法快进合并，请人工介入。"
	exit 1
fi

# === 3. 服务构建循环 ===
for SERVICE in $SERVICES; do
	WORKDIR="$BASE_DIR/$SERVICE"
	# 动态分离 Hash 文件，支持多服务
	HASH_FILE="/root/.last_built_hash_${SERVICE}"

	if [ ! -d "$WORKDIR" ]; then
		log "警告: 目录不存在 $WORKDIR"
		continue
	fi

	# 使用子 shell (...) 避免 cd 造成的路径混乱，虽然绝对路径也安全，但这样更优雅
	(
		cd "$WORKDIR" || exit

		# 获取当前文件夹最后一次变更的 Commit Hash
		CURRENT_HASH=$(git log -n 1 --pretty=format:%H -- .)
		LAST_HASH=$([ -f "$HASH_FILE" ] && cat "$HASH_FILE" || echo "")

		if [ "$CURRENT_HASH" == "$LAST_HASH" ]; then
			log "[$SERVICE] 代码未变更，跳过。"
		else
			log "[$SERVICE] 开始构建..."
			if podman build -t "$SERVICE" .; then
				log "[$SERVICE] 构建成功，重启服务..."

				# 去掉了 daemon-reload，更轻量
				systemctl restart "$SERVICE"

				echo "$CURRENT_HASH" >"$HASH_FILE"
				sleep 2
			else
				log "错误: [$SERVICE] 构建失败！"
			fi
		fi
	)
done

# === 4. 清理 ===
log "清理旧镜像..."
podman image prune -f --filter "until=24h"

log "执行完毕。"
