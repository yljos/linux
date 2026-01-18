#!/bin/bash

# --- 1. 配置参数 ---
PROXY_PORT=7893
# 策略路由标记 (与下方的 nftables 标记一致)
PROXY_FWMARK=0x1 
TABLE_ID=100
# 仅劫持从该网口进入的流量 (局域网入口)
LAN_IF="eth0"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then 
  echo "错误：请使用 sudo 运行此脚本"
  exit 1
fi

echo "正在配置 TProxy 转发规则 (仅限接口: $LAN_IF)..."

# --- 2. 策略路由与路由表配置 ---
# 清理旧规则和路由表
ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null
ip route flush table $TABLE_ID 2>/dev/null

# 让标记为 $PROXY_FWMARK 的数据包查找 100 号路由表
# 该表将流量投递到本地回环口，由 TProxy 接管
ip route add local default dev lo table $TABLE_ID
ip rule add fwmark $PROXY_FWMARK lookup $TABLE_ID priority 100

# --- 3. NFTABLES 规则配置 ---
# 彻底清理旧表
nft delete table ip mihomo 2>/dev/null

# 创建表
nft add table ip mihomo

# 创建 Prerouting 链
nft 'add chain ip mihomo prerouting { type filter hook prerouting priority mangle; policy accept; }'

# ================= 关键逻辑开始 =================

# A. 特殊排除 (最高优先级)
# 1. 排除 DHCP 流量 (UDP 67/68)，确保设备能获取 IP
nft add rule ip mihomo prerouting udp dport { 67, 68 } return

# B. DNS 强行劫持 (修复 DNS 泄露)
# 必须放在“排除私有网段”之前！
# 含义：只要是 TCP/UDP 53 端口，无论目的 IP 是谁(包括路由器网关)，统统转发给 TProxy
nft add rule ip mihomo prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } th dport 53 counter tproxy to :$PROXY_PORT accept

# C. 排除私有网段 (Bypass)
# 排除本地私有网段、组播、广播，确保能直连访问局域网设备和路由器后台
# 注意：此时 DNS(53) 流量已经被上面的规则处理过了，不会走到这一步，所以不会被排除
nft add rule ip mihomo prerouting ip daddr { 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# D. 通用流量劫持
# 1. 标记流量：仅对从 $LAN_IF 进入的剩余 TCP/UDP 流量打标记
nft add rule ip mihomo prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 2. 转发流量：将带标记的流量转发至 Mihomo 监听端口
nft add rule ip mihomo prerouting meta mark $PROXY_FWMARK meta l4proto tcp counter tproxy to :$PROXY_PORT accept
nft add rule ip mihomo prerouting meta mark $PROXY_FWMARK meta l4proto udp counter tproxy to :$PROXY_PORT accept

echo "配置完成！"
echo "DNS 泄露修复验证：客户端 DNS 请求应被重定向到端口 $PROXY_PORT"
echo "检查命令：sudo nft list table ip mihomo"