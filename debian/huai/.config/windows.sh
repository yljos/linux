#!/usr/bin/dash

# 配置
MAC_ADDRESS="00:23:24:67:DF:14"
BROADCAST_IP="10.0.0.255"
TARGET_IP="10.0.0.15"

# 使用 --localnet 扫描全网，并匹配目标 MAC 地址
# 2>/dev/null 屏蔽杂乱的输出
if sudo arp-scan -localnet 2>/dev/null | grep -q "$MAC_ADDRESS"; then
    notify-send "Windows" "主机已在线，直接连接"
else
    # 不在线，发送唤醒包
    wakeonlan -i "$BROADCAST_IP" "$MAC_ADDRESS" >/dev/null 2>&1
    notify-send "WOL" "唤醒魔术包已发送"
    
    # 严格保留你设定的 15 秒
    sleep 15
fi

# 启动 RDP
xfreerdp3 /v:"$TARGET_IP" /u:huai /p:123 /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &