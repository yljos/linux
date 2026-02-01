#!/usr/bin/dash

# 配置
MAC_ADDRESS="00:23:24:67:DF:14"
BROADCAST_IP="10.0.0.255"

wakeonlan -i "$BROADCAST_IP" "$MAC_ADDRESS" >/dev/null 2>&1; then
notify-send "WOL" "唤醒魔术包已发送"

sleep 15
xfreerdp3 /v:10.0.0.15 /u:huai /p:123 /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
