#!/bin/sh

# --- 1. Settings ---
PROXY_PORT=7893
PROXY_FWMARK=0x1
ROUTING_MARK=666
TABLE_ID=100
LAN_IF="eth0"

# Source IP blacklist (These devices bypass the proxy)
SOURCE_BLACKLIST="{ 10.0.0.88 }"

# Check root privileges
if [ "$(id -u)" -ne 0 ]; then
	echo "Error: please run with sudo"
	exit 1
fi

# Clean up function
if [ "$1" = "-s" ]; then
	echo "Removing tproxy rules..."
	while ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null; do :; done
	ip route flush table $TABLE_ID 2>/dev/null
	nft delete table ip mihomo 2>/dev/null
	echo "Cleaned up!"
	exit 0
fi

echo "Configuring tproxy on VyOS..."

# --- 2. Policy Routing ---
while ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null; do :; done
ip route flush table $TABLE_ID 2>/dev/null
ip route add local default dev lo table $TABLE_ID
ip rule add fwmark $PROXY_FWMARK lookup $TABLE_ID priority 100

# --- 3. NFTABLES Initialization ---
nft delete table ip mihomo 2>/dev/null
nft add table ip mihomo
nft "add chain ip mihomo prerouting { type filter hook prerouting priority mangle; policy accept; }"

# ================= Core Logic =================

# 0. Bypass self-generated traffic from proxy
nft add rule ip mihomo prerouting mark $ROUTING_MARK return

# 1. Essential Bypass: DHCP traffic
nft add rule ip mihomo prerouting udp dport { 67, 68 } return

# 2. Source Filter: Skip blacklist devices entirely
nft add rule ip mihomo prerouting iifname "$LAN_IF" ip saddr "$SOURCE_BLACKLIST" return

# 3. Block DoT (853) to force standard DNS
nft add rule ip mihomo prerouting iifname "$LAN_IF" tcp dport 853 reject with tcp reset

# 4. Allow Gateway DNS directly: Let 10.0.0.1:53 handle queries without TProxy interception
nft add rule ip mihomo prerouting iifname "$LAN_IF" ip daddr 10.0.0.1 meta l4proto { tcp, udp } th dport 53 return

# 5. Mark foreign DNS queries to TProxy port (IP header will be preserved by TProxy)
nft add rule ip mihomo prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } th dport 53 meta mark set $PROXY_FWMARK

# 6. Destination Bypass: Skip direct local and private networks
nft add rule ip mihomo prerouting ip daddr { 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# 7. General Hijack: Mark all remaining TCP/UDP traffic
nft add rule ip mihomo prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 8. Apply TProxy action to marked packets
nft add rule ip mihomo prerouting meta mark $PROXY_FWMARK meta l4proto { tcp, udp } tproxy to :$PROXY_PORT accept

echo "Done! TProxy configured successfully."