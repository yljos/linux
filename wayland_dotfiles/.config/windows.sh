#!/usr/bin/sh
# 直接连接指定IP，全部后台运行
(
    notify-send "连接中" "启动 RDP..." && play ~/.config/dunst/connecting.mp3 >/dev/null 2>&1
    xfreerdp3 /v:192.168.31.121 /u:huai /p:110 /sound /dynamic-resolution /cert:ignore >/dev/null 2>&1
) >/dev/null 2>&1 &

