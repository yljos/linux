
(
    sleep 2  # Wait for dwm and network to be fully ready
    
    # 延迟 2 秒启动，并将所有报错输出到日志
    [ -f /home/huai/.config/status.sh ] && /bin/bash /home/huai/.config/status.sh &
) &
exec dbus-run-session dwm