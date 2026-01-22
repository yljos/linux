#!/bin/bash

# --- 1. 配置参数 ---
PROXY_PORT=7893
PROXY_FWMARK=0x1 
TABLE_ID=100
LAN_IF="eth0"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then 
  echo "错误：请使用 sudo 运行此脚本"
  exit 1
fi

echo "正在配置 Sing-box TProxy (智能防泄露版)..."

# --- 2. 策略路由 ---
ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null
ip route flush table $TABLE_ID 2>/dev/null
ip route add local default dev lo table $TABLE_ID
ip rule add fwmark $PROXY_FWMARK lookup $TABLE_ID priority 100

# --- 3. NFTABLES 规则配置 ---
nft delete table ip sing-box 2>/dev/null
nft add table ip sing-box
nft 'add chain ip sing-box prerouting { type filter hook prerouting priority mangle; policy accept; }'

# ================= 核心逻辑优化 =================

# 1. 绝对排除：DHCP 必须直连
nft add rule ip sing-box prerouting udp dport { 67, 68 } return

# 2. 绝对劫持：DNS (UDP/TCP 53)
# 只要是 53 端口，不管目标 IP 是公网还是内网，先打标记送走
# 配合 Sing-box 的 sniff 功能，这会完美处理所有 DNS
# nft add rule ip sing-box prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } th dport 53 meta mark set $PROXY_FWMARK
# nft add rule ip sing-box prerouting meta mark $PROXY_FWMARK meta l4proto { tcp, udp } counter tproxy to :$PROXY_PORT accept
nft add rule ip sing-box PREROUTING udp dport 53 redirect to :1053

# 3. 条件排除：私有网段 (Bypass)
# 只有非 DNS 的内网流量才会走到这一步，被放行
nft add rule ip sing-box prerouting ip daddr { 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# 4. 通用劫持：剩余流量
# 仅对从 LAN 口进入的流量打标记
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 转发流量
nft add rule ip sing-box prerouting meta mark $PROXY_FWMARK meta l4proto tcp counter tproxy to :$PROXY_PORT accept
nft add rule ip sing-box prerouting meta mark $PROXY_FWMARK meta l4proto udp counter tproxy to :$PROXY_PORT accept

echo "配置完成！DNS 和流量已强制接管。"
