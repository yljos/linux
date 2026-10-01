#!/bin/sh
# Manage nftables set on auth/deauth

ACTION=$1
MAC=$2

case "$ACTION" in
    auth_client)
        nft add element inet fw4 clash_mac_allowlist "{ $MAC }"
        ;;
    client_deauth)
        nft delete element inet fw4 clash_mac_allowlist "{ $MAC }"
        ;;
esac

exit 0