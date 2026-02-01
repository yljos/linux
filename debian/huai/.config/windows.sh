#!/usr/bin/dash

# 配置
MAC_ADDRESS="00:23:24:67:DF:14"
BROADCAST_IP="10.0.0.255"

# 发送唤醒指令
if wakeonlan -i "$BROADCAST_IP" "$MAC_ADDRESS" >/dev/null 2>&1; then
    notify-send "WOL" "唤醒魔术包已发送"
else
    notify-send "错误" "唤醒失败，请检查 wakeonlan 是否安装"
    exit 1
fi