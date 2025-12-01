#!/usr/bin/env bash

# 1. 遍历：只获取 镜像名 和 容器名
podman ps --format "{{.Image}} {{.Names}}" | while read image name; do

	# === 分支 A: 本地镜像 ===
	# 包含 localhost 则跳过
	if [[ "$image" == *"localhost"* ]]; then
		continue
	fi

	# === 分支 B: 远程镜像 ===
	# 1. 拉取最新镜像，静默处理输出
	podman image pull "$image" >/dev/null 2>&1

	# 2. 获取【远程最新】的镜像 ID (SHA256)
	latest_id=$(podman image inspect --format "{{.Id}}" "$image" 2>/dev/null)

	# 3. 获取【容器当前】的镜像 ID
	running_id=$(podman container inspect --format "{{.Image}}" "$name" 2>/dev/null)

	# 4. 极简比对：如果不相等，说明容器还在用旧镜像
	if [[ "$running_id" != "$latest_id" ]]; then
		echo "[$name] 发现更新，正在重启..."
		systemctl --user restart "$name"
	fi
done

# 2. 清理：强力清除所有未使用镜像 (-a:删所有未运行; -f:不确认)
podman image prune -af >/dev/null 2>&1

echo "更新完成"
