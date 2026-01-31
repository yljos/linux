#!/usr/bin/env bash

# 使用 mpv 静默播放启动音效
mpv --no-video --quiet ~/.config/dunst/xp.wav &

# 启动 Firefox ESR
# 只有在检测不到 "firefox-esr" 进程时才启动
if ! pgrep -f "firefox-esr" &>/dev/null; then
    sleep 3
    firefox-esr >/tmp/firefox_startup.log 2>&1 &
fi

# 启动 Telegram
if ! pgrep -x "Telegram" &>/dev/null; then
    Telegram &
fi

# 自动切换壁纸脚本
if [ -f ~/.config/wallpaperautochange.sh ]; then
    /bin/bash ~/.config/wallpaperautochange.sh &
fi

# 关机脚本 (监听或其他用途)
if [ -f ~/.config/shutdown.sh ]; then
    /bin/bash ~/.config/shutdown.sh &
fi

# 开启数字小键盘
if command -v numlockx &>/dev/null; then
    numlockx &
fi

# 窗口合成器
if ! pgrep -x "picom" &>/dev/null; then
    picom -b
fi

# 输入法
if ! pgrep -x "fcitx5" &>/dev/null; then
    fcitx5 -d
fi

# 通知服务
if ! pgrep -x "dunst" &>/dev/null; then
    dunst &
fi

sleep 3

# DWM 状态栏
if [ -f ~/.config/dwm/dwm_status.sh ] && ! pgrep -f "bash.*dwm_status.sh" &>/dev/null; then
    /bin/bash ~/.config/dwm/dwm_status.sh &
fi