#!/bin/bash

# --- 1. Settings ---
PROXY_PORT=7893
PROXY_FWMARK=0x1
TABLE_ID=100
LAN_IF="eth0"

# Source IP whitelist (No spaces inside braces for shell safety)
SOURCE_WHITELIST="{10.0.0.8,10.0.0.15,10.0.0.21,10.0.0.25}"

# Check root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: please run with sudo"
    exit 1
fi

echo "Configuring sing-box TProxy (Global DNS + Source Whitelist)..."

# --- 2. Policy Routing ---
ip rule del fwmark $PROXY_FWMARK lookup $TABLE_ID 2>/dev/null
ip route flush table $TABLE_ID 2>/dev/null
ip route add local default dev lo table $TABLE_ID
ip rule add fwmark $PROXY_FWMARK lookup $TABLE_ID priority 100

# --- 3. NFTABLES Initialization (CRITICAL) ---
# Clean old rules and create table/chain before adding rules
nft delete table ip sing-box 2>/dev/null
nft add table ip sing-box
nft 'add chain ip sing-box prerouting { type filter hook prerouting priority mangle; policy accept; }'

# ================= Core Logic =================

# 1. Essential Bypass: DHCP traffic must be direct
nft add rule ip sing-box prerouting udp dport { 67, 68 } return

# 2. [REJECT FIRST] Block DoT (853) for ALL devices
# Stop encrypted DNS early to force fallback to standard DNS
nft add rule ip sing-box prerouting iifname "$LAN_IF" tcp dport 853 reject with tcp reset

# 3. [MARK SECOND] DNS Hijack: Port 53 (UDP/TCP) for ALL devices
# Capture plain DNS for sniffing and redirection
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } th dport 53 meta mark set $PROXY_FWMARK

# 4. Source Filter: Skip any device NOT in the whitelist (EXCEPT for DNS which is already marked)
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta mark != $PROXY_FWMARK ip saddr != "$SOURCE_WHITELIST" return

# 5. Destination Bypass: For whitelisted devices, skip private networks
nft add rule ip sing-box prerouting ip daddr { 127.0.0.0/8, 10.0.0.0/24, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4, 255.255.255.255 } return

# 6. General Hijack: Mark remaining traffic from whitelisted devices
nft add rule ip sing-box prerouting iifname "$LAN_IF" meta l4proto { tcp, udp } meta mark set $PROXY_FWMARK

# 7. Apply TProxy action to ALL marked packets
nft add rule ip sing-box prerouting meta mark $PROXY_FWMARK meta l4proto { tcp, udp } tproxy to :$PROXY_PORT accept

echo "Done! Whitelist: $SOURCE_WHITELIST"