#!/usr/bin/env bash

# 1. 仅更新正在运行的容器镜像
podman ps --format "{{.Image}} {{.Names}}" | while read image name; do
	echo "拉取镜像: $image"
	podman image pull "$image"
	echo "重启容器: $name"
	clean_name="${name#systemd-}"
	systemctl --user restart "$clean_name"
done

# 2. 清理无用镜像
echo "清理无用镜像..."
podman image prune -af

echo "批量更新完成。"
