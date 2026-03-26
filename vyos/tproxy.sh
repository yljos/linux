#!/bin/bash

# --- 1. Settings ---
PROXY_PORT=7893
PROXY_FWMARK=0x1
TABLE_ID=100
LAN_IF="eth0"

# Source IP whitelist (Only these devices get full proxy)
SOURCE_WHITELIST="{10.0.0.8,10.0.0.15,10.0.0.21,10.0.0.25,10.0.0.121}"

# Check root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: please run with sudo"
    exit 1
fi

echo "Configuring sing-box TProxy on VyOS (Enhanced Global DNS)..."

# --- 2. Policy Routing ---
ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null
ip route flush table $TABLE_ID 2>/dev/null
ip route add local default dev lo table $TABLE_ID
ip rule add fwmark $PROXY_FWMARK lookup $TABLE_ID priority 100

# --- 3. NFTABLES Initialization ---
nft delete table ip sing-box 2>/dev/null
nft add table ip sing-box
nft 'add chain ip sing-box prerouting { type filter hook prerouting priority mangle; policy accept; }'

# ================= Core Logic =================

# 1. Essential Bypass: DHCP traffic must be direct
nft add rule ip sing-box prerouting udp dport { 67, 68 } return

# 2. [REJECT FIRST] Block DoT (853) for ALL devices
nft add rule ip sing-box prerouting iifname "$LAN_IF" tcp dport 853 reject with tcp reset

# 3. [GLOBAL MARK] DNS Hijack (Port 53) for ALL devices
# This captures DNS packets regardless of the destination IP (1.1.1.1 or 10.0.0.1)
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } th dport 53 meta mark set $PROXY_FWMARK

# 4. Source Filter: Skip non-whitelist devices IF it's not a DNS packet
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta mark != $PROXY_FWMARK ip saddr != "$SOURCE_WHITELIST" return

# 5. [FIXED] Destination Bypass: Skip local traffic ONLY IF it's not a DNS packet
# This ensures even if a client uses 10.0.0.1 as DNS, it gets proxied
nft add rule ip sing-box prerouting meta mark != $PROXY_FWMARK ip daddr { 127.0.0.0/8, 10.0.0.0/24, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# 6. General Hijack: Mark all remaining traffic from whitelist devices
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 7. Apply TProxy action to ALL marked packets (DNS + Whitelisted Traffic)
nft add rule ip sing-box prerouting meta mark $PROXY_FWMARK meta l4proto { tcp, udp } tproxy to :$PROXY_PORT accept

echo "Done! Even gateway DNS (10.0.0.1) is now successfully hijacked to sing-box."