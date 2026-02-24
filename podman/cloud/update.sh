#!/bin/bash

# === 配置区域 ===
BASE_DIR="$HOME/linux/free"
SERVICES="convert" # 如果以后有多个，用空格隔开: "convert web"
LOCK_FILE="/tmp/update.sh.lock"

# === 环境与函数 ===
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/libexec/podman:/usr/lib/podman
# 确保后台任务能正确访问用户级 systemd (Debian 下非常重要)
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

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
    log "检测到无更新，退出。"
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
    HASH_FILE="$HOME/.last_built_hash_${SERVICE}"

    if [ ! -d "$WORKDIR" ]; then
        log "警告: 目录不存在 $WORKDIR"
        continue
    fi

    (
        cd "$WORKDIR" || exit

        CURRENT_HASH=$(git log -n 1 --pretty=format:%H -- .)
        LAST_HASH=$([ -f "$HASH_FILE" ] && cat "$HASH_FILE" || echo "")

        if [ "$CURRENT_HASH" == "$LAST_HASH" ]; then
            log "[$SERVICE] 代码未变更，跳过。"
        else
            log "[$SERVICE] 开始构建..."
            # 隐藏标准输出，保持日志极简
            if podman build -t "$SERVICE" . > /dev/null; then
                log "[$SERVICE] 构建成功，重启服务..."

                # 执行用户级服务重启
                systemctl --user restart "$SERVICE"

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
# 同样隐藏清理操作的常规输出
podman image prune -f --filter "until=24h" > /dev/null

log "执行完毕。"