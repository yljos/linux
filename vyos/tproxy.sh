#!/bin/bash

# --- 1. Settings ---
PROXY_PORT=7893
PROXY_FWMARK=0x1
TABLE_ID=100
LAN_IF="eth0"

# Source IP blacklist (These devices bypass the proxy and DNS hijacking)
SOURCE_BLACKLIST="{10.0.0.6}"

# Check root privileges
if [ "$EUID" -ne 0 ]; then
	echo "Error: please run with sudo"
	exit 1
fi

echo "Configuring mihomo TProxy on VyOS..."

# --- 2. Policy Routing ---
# Loop to ensure all duplicated rules are deleted
while ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null; do :; done
ip route flush table $TABLE_ID 2>/dev/null
ip route add local default dev lo table $TABLE_ID
ip rule add fwmark $PROXY_FWMARK lookup $TABLE_ID priority 100

# --- 3. NFTABLES Initialization ---
nft delete table ip mihomo 2>/dev/null
nft add table ip mihomo
nft "add chain ip mihomo prerouting { type filter hook prerouting priority mangle; policy accept; }"

# ================= Core Logic =================

# 1. Essential Bypass: DHCP traffic must be direct
nft add rule ip mihomo prerouting udp dport { 67, 68 } return

# 2. Source Filter: Skip blacklist devices entirely (Bypasses DNS and all traffic)
nft add rule ip mihomo prerouting iifname $LAN_IF ip saddr $SOURCE_BLACKLIST return

# 3. Block DoT (853)
nft add rule ip mihomo prerouting iifname $LAN_IF tcp dport 853 reject with tcp reset

# 4. Mark DNS (Port 53)
nft add rule ip mihomo prerouting iifname $LAN_IF meta l4proto { tcp, udp } th dport 53 meta mark set $PROXY_FWMARK

# 5. Destination Bypass: Skip local traffic ONLY IF it's not a DNS packet (Fixed to 10.0.0.0/8)
nft add rule ip mihomo prerouting meta mark != $PROXY_FWMARK ip daddr { 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# 6. General Hijack: Mark all remaining traffic
nft add rule ip mihomo prerouting iifname $LAN_IF meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 7. Apply TProxy action to ALL marked packets (DNS + Proxied Traffic)
nft add rule ip mihomo prerouting meta mark $PROXY_FWMARK meta l4proto { tcp, udp } tproxy to :$PROXY_PORT accept

echo "Done! Blacklisted devices bypass mihomo."
