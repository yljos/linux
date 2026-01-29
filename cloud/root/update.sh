#!/bin/bash

# 定义日志输出函数
log() {
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 修正环境变量 (确保能找到 podman 和 netavark)
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/libexec/podman:/usr/lib/podman

# 定义变量
BASE_DIR="/root/linux/free"
# === 修改点：将服务列表改为 convert ===
SERVICES="convert"

# 记录上次构建成功的 Hash 值的文件名
HASH_FILE=".last_built_hash"

log "脚本启动"

# 1. 进入父目录执行 Git Pull
cd "$BASE_DIR" || {
	log "错误: 无法进入目录 $BASE_DIR"
	exit 1
}

# 捕获 git pull 的输出
log "正在检查 Git 仓库更新..."
GIT_OUTPUT=$(git pull)
EXIT_CODE=$?

# 检查 git pull 是否执行出错
if [ $EXIT_CODE -ne 0 ]; then
	log "错误: git pull 执行失败"
	exit 1
fi

# 2. 循环检查每个服务
for SERVICE in $SERVICES; do
	WORKDIR="$BASE_DIR/$SERVICE"

	# 检查目录是否存在
	if [ ! -d "$WORKDIR" ]; then
		log "警告: 服务目录不存在，跳过: $WORKDIR"
		continue
	fi

	if cd "$WORKDIR"; then
		# === 核心逻辑：获取哈希值 ===
		# 获取该目录(.)最近一次提交的完整 Commit Hash
		CURRENT_HASH=$(git log -n 1 --pretty=format:%H -- .)

		# 读取上次构建成功的 Hash (如果文件不存在则为空)
		if [ -f "$HASH_FILE" ]; then
			LAST_HASH=$(cat "$HASH_FILE")
		else
			LAST_HASH=""
		fi

		# === 核心逻辑：对比哈希值 ===
		if [ "$CURRENT_HASH" == "$LAST_HASH" ]; then
			log "[$SERVICE] 目录无变更 (Hash: ${CURRENT_HASH:0:7})，跳过构建。"
		else
			log "[$SERVICE] 检测到变更或无构建记录"
			log "  -> 旧 Hash: ${LAST_HASH:0:7}"
			log "  -> 新 Hash: ${CURRENT_HASH:0:7}"
			log "  -> 正在构建镜像: $SERVICE"

			# 执行构建
			if podman build -t "$SERVICE" .; then
				log "[$SERVICE] 构建成功，正在重启服务..."

				# 重启服务 (假设 systemd 服务名也叫 convert)
				systemctl daemon-reload
				systemctl restart "$SERVICE"

				# === 关键：构建成功后，更新本地 Hash 记录 ===
				echo "$CURRENT_HASH" >"$HASH_FILE"
				log "[$SERVICE] Hash 记录已更新。"

				# 缓冲一下，避免 CPU 飙升
				sleep 3
			else
				log "错误: [$SERVICE] 构建镜像失败！Hash 记录未更新，下次将重试。"
			fi
		fi
	else
		log "警告: 无法进入服务目录 $WORKDIR"
	fi
done

log "正在清理虚悬镜像..."
podman image prune -f

log "脚本执行完毕。"
