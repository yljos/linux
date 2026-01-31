#!/usr/bin/env bash

# 1. 切换 fcitx5 输入法状态
fcitx5-remote -t

# 2. 发送信号给 dwl_status.sh 立即刷新

pkill -RTMIN+3 -f dwl_status.sh
