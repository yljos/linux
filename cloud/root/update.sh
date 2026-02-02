#!/bin/bash

# 定义日志输出函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 修正环境变量
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/libexec/podman:/usr/lib/podman

# 定义变量
BASE_DIR="/root/linux/free"
SERVICES="convert"
HASH_FILE=".last_built_hash"

log "脚本启动: 检查远程更新..."

# 1. 进入父目录
cd "$BASE_DIR" || {
    log "错误: 无法进入目录 $BASE_DIR"
    exit 1
}

# 2. 核心改进：执行 fetch 并对比
git fetch --quiet origin
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse @{u}) # 获取当前分支追踪的远程分支 Hash

if [ "$LOCAL_HASH" == "$REMOTE_HASH" ]; then
    log "远程仓库无更新 (Hash: ${LOCAL_HASH:0:7})，脚本退出。"
    exit 0
fi

log "检测到远程更新: $LOCAL_HASH -> $REMOTE_HASH"

# 3. 只有有更新时才执行合并
if ! git merge --ff-only --quiet; then
    log "错误: 无法执行快进合并，请手动检查冲突。"
    exit 1
fi

# 4. 循环检查并构建服务
for SERVICE in $SERVICES; do
    WORKDIR="$BASE_DIR/$SERVICE"

    if [ ! -d "$WORKDIR" ]; then
        log "警告: 服务目录不存在: $WORKDIR"
        continue
    fi

    if cd "$WORKDIR"; then
        CURRENT_HASH=$(git log -n 1 --pretty=format:%H -- .)
        LAST_HASH=$( [ -f "$HASH_FILE" ] && cat "$HASH_FILE" || echo "" )

        if [ "$CURRENT_HASH" == "$LAST_HASH" ]; then
            log "[$SERVICE] 本次更新未涉及该目录，跳过构建。"
        else
            log "[$SERVICE] 正在构建镜像..."
            if podman build -t "$SERVICE" .; then
                log "[$SERVICE] 构建成功，重启服务..."
                systemctl daemon-reload
                systemctl restart "$SERVICE"
                echo "$CURRENT_HASH" > "$HASH_FILE"
                sleep 3
            else
                log "错误: [$SERVICE] 构建失败！"
            fi
        fi
    fi
done

# 只有真正执行了更新和构建，清理才有意义
log "正在清理 24 小时前的虚悬镜像..."
podman image prune -f --filter "until=24h"

log "脚本执行完毕。"