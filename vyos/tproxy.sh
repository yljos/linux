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

# 创建 Prerouting 链 (使用单引号包裹防止 VyOS Shell 语法冲突)
nft 'add chain ip mihomo prerouting { type filter hook prerouting priority mangle; policy accept; }'

# A. 排除逻辑 (Bypass)
# 1. 排除 DHCP 流量 (防止设备无法获取 IP)
nft add rule ip mihomo prerouting udp dport { 67, 68 } return

# 2. 排除本地私有网段、组播、广播 (防止局域网内访无法直连)
# 即使只劫持 eth0，也必须排除这些，否则你无法通过 eth0 访问路由器自身或局域网其他设备
nft add rule ip mihomo prerouting ip daddr { 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# B. 劫持逻辑
# 1. 严格限制：仅对从 $LAN_IF 进入的流量打上策略路由标记
nft add rule ip mihomo prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 2. 将带标记的流量转发至 Mihomo 监听端口
# 添加 counter 以便通过 'nft list table' 查看是否有流量命中
nft add rule ip mihomo prerouting meta mark $PROXY_FWMARK meta l4proto tcp counter tproxy to :$PROXY_PORT accept
nft add rule ip mihomo prerouting meta mark $PROXY_FWMARK meta l4proto udp counter tproxy to :$PROXY_PORT accept

echo "配置完成！"
echo "检查命令：sudo nft list table ip mihomo"