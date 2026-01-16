#!/bin/bash

# 定义日志输出函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 修正环境变量 (确保能找到 podman 和 netavark)
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/libexec/podman:/usr/lib/podman

# 定义变量
BASE_DIR="/root/linux/free"
SERVICES="sing-box clash"

log "脚本启动"

# 进入父目录执行一次性更新
cd "$BASE_DIR" || {
    log "错误: 无法进入目录 $BASE_DIR"
    exit 1
}

# 捕获 git pull 的输出
GIT_OUTPUT=$(git pull)
EXIT_CODE=$?

# 检查 git pull 是否执行出错
if [ $EXIT_CODE -ne 0 ]; then
    log "错误: git pull 执行失败"
    exit 1
fi

# 检查是否有更新
if echo "$GIT_OUTPUT" | grep -q "Already up to date"; then
    log "当前已是最新，无需更新。"
    exit 0
fi

log "检测到代码更新，开始构建服务..."

# 循环构建和重启服务
for SERVICE in $SERVICES; do
    WORKDIR="$BASE_DIR/$SERVICE"

    if cd "$WORKDIR"; then
        log "正在构建镜像: $SERVICE"
        if podman build -t "$SERVICE" .; then
            log "构建成功，正在重启服务: $SERVICE"
            systemctl restart "$SERVICE"

            # 缓冲一下，避免 CPU 飙升
            sleep 3
        else
            log "错误: $SERVICE 构建镜像失败"
        fi
    else
        log "警告: 无法进入服务目录 $WORKDIR"
    fi
done

log "正在清理虚悬镜像..."
podman image prune -f

log "脚本执行完毕。"