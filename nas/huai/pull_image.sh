#!/usr/bin/env bash

# 1. Iterate: get Image and Container Name
podman ps --format "{{.Image}} {{.Names}}" | while read image name; do

	# === Branch A: Local Images ===
	# Skip if image is from localhost
	if [[ "$image" == *"localhost"* ]]; then
		continue
	fi

	# === Branch B: Remote Images ===
	# 1. Pull latest image silently
	podman image pull "$image" >/dev/null 2>&1

	# 2. Get the Latest Image ID
	latest_id=$(podman image inspect --format "{{.Id}}" "$image" 2>/dev/null)

	# 3. Get the Running Container's Image ID
	running_id=$(podman container inspect --format "{{.Image}}" "$name" 2>/dev/null)

	# 4. Comparison: Restart via sv if IDs mismatch
	if [[ "$running_id" != "$latest_id" ]]; then
		echo "[$name] Update detected, restarting..."
		sv restart "$name"
	fi
done

# 2. Cleanup: Force remove all unused images
podman image prune -af >/dev/null 2>&1

echo "Update complete"