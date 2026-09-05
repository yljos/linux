
(
    sleep 1  # Wait for dwm and network to be fully ready
    
    # 延迟 1 秒启动，并将所有报错输出到日志
    [ -f /home/huai/.config/status.sh ] && /bin/bash /home/huai/.config/status.sh &

) &
# pipewire
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/tmp/user-$(id -u)"
    [ ! -d "$XDG_RUNTIME_DIR" ] && mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
fi
pipewire &
wireplumber &
pipewire-pulse &
exec dwm