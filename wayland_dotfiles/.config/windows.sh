#!/usr/bin/sh
# 直接连接指定IP，全部后台运行
(
    notify-send "连接中" "启动 RDP..." && play ~/.config/dunst/connecting.mp3 >/dev/null 2>&1
    xfreerdp3 /v:192.168.31.156 /u:huai /p:110 /sound /dynamic-resolution /cert:ignore >/dev/null 2>&1 &
    RDP_PID=$!
    sleep 5
    if kill -0 "$RDP_PID" 2>/dev/null; then
        notify-send "连接成功" "RDP 会话已建立" && play ~/.config/dunst/success.mp3 >/dev/null 2>&1
    else
        notify-send "连接失败" "RDP 连接建立失败" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
    fi
) >/dev/null 2>&1 &

