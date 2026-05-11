#!/bin/bash

# === Configuration ===
BASE_DIR="$HOME/linux"
SERVICES="convert" # Space separated for multiple: "convert web"
LOCK_FILE="/tmp/update.sh.lock"

# === Environment & Functions ===
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# === 1. Concurrency Lock ===
exec 9>"$LOCK_FILE" || exit 1
flock -n 9 || {
    log "Instance already running, exiting."
    exit 0
}

log "Script started: Checking for remote updates..."

# === 2. Update Check ===
cd "$BASE_DIR" || {
    log "Error: Cannot enter directory $BASE_DIR"
    exit 1
}

# Fetch metadata only
git fetch --quiet origin

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse @{u})

if [ "$LOCAL_HASH" == "$REMOTE_HASH" ]; then
    log "No updates detected, exiting."
    exit 0
fi

log "Remote updates detected: ${LOCAL_HASH:0:7} -> ${REMOTE_HASH:0:7}"

if ! git merge --ff-only --quiet; then
    log "Error: Cannot fast-forward merge, manual intervention required."
    exit 1
fi

# === 3. Service Build Loop ===
for SERVICE in $SERVICES; do
    WORKDIR="$BASE_DIR/$SERVICE"
    HASH_FILE="$HOME/.last_built_hash_${SERVICE}"

    if [ ! -d "$WORKDIR" ]; then
        log "Warning: Directory does not exist $WORKDIR"
        continue
    fi

    (
        cd "$WORKDIR" || exit

        CURRENT_HASH=$(git log -n 1 --pretty=format:%H -- .)
        LAST_HASH=$([ -f "$HASH_FILE" ] && cat "$HASH_FILE" || echo "")

        if [ "$CURRENT_HASH" == "$LAST_HASH" ]; then
            log "[$SERVICE] Code unchanged, skipping."
        else
            log "[$SERVICE] Starting build..."
            # Hide standard output
            if podman build -t "$SERVICE" . >/dev/null; then
                log "[$SERVICE] Build successful, restarting service..."

                # Restart service via systemd (Debian default)
                systemctl restart "$SERVICE"

                echo "$CURRENT_HASH" >"$HASH_FILE"
                sleep 2
            else
                log "Error: [$SERVICE] Build failed!"
            fi
        fi
    )
done

# === 4. Cleanup ===
log "Cleaning up old images..."
# Hide cleanup output
podman image prune -f --filter "until=24h" >/dev/null

log "Execution completed."