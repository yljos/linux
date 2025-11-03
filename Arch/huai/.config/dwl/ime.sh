#!/usr/bin/env bash
#
# 包装脚本：切换 fcitx5 输入法，并发送信号通知 dwl_status 刷新

# 1. 切换输入法
fcitx5-remote -t

# 2. 使用 Python 脚本通知状态栏更新输入法显示
python3 "$HOME/.config/dwl/notify_ime.py" 2>/dev/null
