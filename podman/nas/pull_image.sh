#!/usr/bin/env bash

# 1. 遍历：直接获取 镜像名、容器名、当前运行的镜像ID
podman ps --format "{{.Image}} {{.Names}} {{.ImageID}}" | while read image name running_id; do

	# === 分支 A: 本地镜像 ===
	# 极简：既然不更新，就不需要任何输出，直接跳过
	if [[ "$image" == *"localhost"* ]]; then
		continue
	fi

	# === 分支 B: 远程镜像 ===
	# 1. 拉取最新镜像（静默）
	podman image pull "$image" >/dev/null 2>&1

	# 2. 获取拉取后的本地最新 ID
	latest_id=$(podman image inspect --format "{{.Id}}" "$image" 2>/dev/null)

	# 3. 极简比对：运行中的 ID vs 拉取后的最新 ID
	if [[ "$running_id" != "$latest_id" ]]; then
		# 只有真正需要重启时才说话
		echo "[$name] 发现更新，正在重启..."
		systemctl --user restart "$name"
	fi
done

# 2. 清理：删悬空镜像
podman image prune -af >/dev/null 2>&1

echo "更新完成"
