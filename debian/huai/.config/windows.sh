#!/usr/bin/dash

# 配置
MAC_ADDRESS="00:23:24:67:DF:14"
BROADCAST_IP="10.0.0.255"
TARGET_IP="10.0.0.15"

# 修复：增加了 if 和 fi
if wakeonlan -i "$BROADCAST_IP" "$MAC_ADDRESS" >/dev/null 2>&1; then
    notify-send "Windows" "唤醒魔术包已发送，等待启动..."
fi

sleep 15

# 启动 RDP
xfreerdp3 /v:"$TARGET_IP" /u:huai /p:123 /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
