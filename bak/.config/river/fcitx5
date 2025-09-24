#!/usr/bin/sh
# 杀死之前的定时器
pkill -f "sleep 30.*killall fcitx5" 2>/dev/null

# 确保 fcitx5 运行
if ! pgrep -x fcitx5 > /dev/null; then
    fcitx5 -d &
    sleep 2 # 等待 fcitx5 启动 
fi

# 切换输入法
fcitx5-remote -t

# 30秒后自动关闭fcitx5（后台运行）
(sleep 30 && killall fcitx5 2>/dev/null) &
