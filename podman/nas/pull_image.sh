#!/usr/bin/env bash

echo "开始更新镜像..."

# 1. 遍历正在运行的容器
podman ps --format "{{.Image}} {{.Names}}" | while read image name; do
    
    # 假设服务名等于容器名
    service_name="$name"

    echo "--------------------------------------------------"
    
    # === 分支 A: 本地镜像 (localhost) ===
    # 逻辑：无法 pull，强制重启以应用可能的本地新构建
    if [[ "$image" == *"localhost"* ]]; then
        echo "本地镜像: $image"
        echo "跳过"

    # === 分支 B: 远程镜像 (其他) ===
    # 逻辑：拉取 -> 比对 ID -> 只有 ID 变了才重启
    else
        echo "远程镜像: $image"
        
        # 1. 记录旧 ID
        old_id=$(podman image inspect --format "{{.Id}}" "$image" 2>/dev/null)

        # 2. 拉取新镜像 (静默)
        podman image pull "$image" > /dev/null

        # 3. 记录新 ID
        new_id=$(podman image inspect --format "{{.Id}}" "$image" 2>/dev/null)

        # 4. 核心比对
        if [[ "$old_id" != "$new_id" ]]; then
            echo "发现新版本 ($old_id -> $new_id)"
            echo "重启服务: $service_name"
            systemctl --user restart "$service_name"
        else
            echo "镜像无更新"
        fi
    fi
done

echo "--------------------------------------------------"

# 2. 清理无用镜像
echo "清理无用镜像..."
podman image prune -af

echo "更新完成。"