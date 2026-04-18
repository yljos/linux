# VyOS 2025.11 Configuration Notes

## 1. Install
```bash
# Enter image installation mode
install image
```
## 2. Base Connectivity
### Enter Config Mode
```bash
configure
```
### Set PPPoE Username
```bash
set interfaces pppoe pppoe0 authentication username 'YOUR_USERNAME'
```

### Set PPPoE Password
```bash
set interfaces pppoe pppoe0 authentication password 'YOUR_PASSWORD'
```

### LAN Interface
```bash
# Define LAN interface
set interfaces ethernet eth0 address 10.0.0.1/24
set interfaces ethernet eth0 description LAN
```

### PPPoE Interface Binding
```bash
# Bind PPPoE to physical interface eth1
set interfaces ethernet eth1 description WAN
set interfaces pppoe pppoe0 source-interface eth1
```

### PPPoE MTU & MSS
```bash
# Optimize for PPPoE
set interfaces pppoe pppoe0 mtu 1492
set interfaces pppoe pppoe0 ip adjust-mss clamp-mss-to-pmtu
```

## 3. DHCP Server
```bash
# Configure DHCP for LAN
set service dhcp-server shared-network-name LAN authoritative
set service dhcp-server shared-network-name LAN option ntp-server 10.0.0.1
set service dhcp-server shared-network-name LAN option time-zone UTC
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 subnet-id 1
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 option default-router 10.0.0.1
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 option name-server 10.0.0.1
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 range 0 start 10.0.0.101
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 range 0 stop 10.0.0.200
```

## 4. DNS Forwarding
```bash
# DNS forwarding settings
set system name-server pppoe0
set service dns forwarding cache-size 0
set service dns forwarding allow-from 10.0.0.0/24
set service dns forwarding system
```

### DNS Listen Address
```bash
# Listen on loopback only (for sing-box compatibility)
delete service dns forwarding listen-address 10.0.0.1
set service dns forwarding listen-address 127.0.0.1
```

## 5. SSH Service
```bash
# SSH Access and Public Key
set service ssh listen-address 10.0.0.1
set system login user vyos authentication public-keys admin type ssh-ed25519
set system login user vyos authentication public-keys admin key AAAAC3NzaC1lZDI1NTE5AAAAIJiWQNpWDw/+0lhI1KeGL1MI0MiHhQ2HYe/qhjmddGni
```

## 6. NTP & Timezone
```bash
# Time synchronization
set system time-zone UTC
set service ntp server ntp.aliyun.com
delete service ntp server time1.vyos.net
delete service ntp server time2.vyos.net
delete service ntp server time3.vyos.net
```

## 7. NAT (Masquerade)
```bash
# Source NAT for outbound traffic
set nat source rule 100 outbound-interface name pppoe0
set nat source rule 100 source address 10.0.0.0/24
set nat source rule 100 translation address masquerade
```

## 8. Firewall Policy (Rulesets)

### WAN to LAN
```bash
# State-based rules for WAN to LAN
set firewall ipv4 name WAN-LAN default-action drop
set firewall ipv4 name WAN-LAN rule 1 action accept
set firewall ipv4 name WAN-LAN rule 1 state established
set firewall ipv4 name WAN-LAN rule 1 state related
```

### WAN to Local
```bash
# Protect router from WAN access
set firewall ipv4 name WAN-LOCAL default-action drop
set firewall ipv4 name WAN-LOCAL rule 1 action accept
set firewall ipv4 name WAN-LOCAL rule 1 state established
set firewall ipv4 name WAN-LOCAL rule 1 state related
```

### Internal Traffic
```bash
# Default accept for internal flows
set firewall ipv4 name LAN-WAN default-action accept
set firewall ipv4 name LAN-LOCAL default-action accept
set firewall ipv4 name LOCAL-LAN default-action accept
set firewall ipv4 name LOCAL-WAN default-action accept
```

## 9. Firewall Zones

### LOCAL Zone
```bash
# Define LOCAL zone policy
set firewall zone LOCAL local-zone
set firewall zone LOCAL default-action drop
set firewall zone LOCAL from LAN firewall name LAN-LOCAL
set firewall zone LOCAL from WAN firewall name WAN-LOCAL
```

### LAN Zone
```bash
# Define LAN zone policy
set firewall zone LAN member interface eth0
set firewall zone LAN default-action drop
set firewall zone LAN from LOCAL firewall name LOCAL-LAN
set firewall zone LAN from WAN firewall name WAN-LAN
```

### WAN Zone
```bash
# Define WAN zone policy
set firewall zone WAN member interface pppoe0
set firewall zone WAN default-action drop
set firewall zone WAN from LAN firewall name LAN-WAN
set firewall zone WAN from LOCAL firewall name LOCAL-WAN
```

## 10. Containers (TProxy)

### Mihomo
```bash
# Mihomo container setup
set container name mihomo image 'docker.io/metacubex/mihomo:latest'
set container name mihomo capability 'net-admin'
set container name mihomo capability 'net-raw'
set container name mihomo allow-host-networks
set container name mihomo volume config destination '/root/.config/mihomo'
set container name mihomo volume config source '/config/mihomo/'
set container name mihomo restart 'on-failure'
```

### Sing-box
```bash
# Sing-box container setup
set container name sing-box image 'ghcr.io/sagernet/sing-box:latest'
set container name sing-box capability 'net-admin'
set container name sing-box capability 'net-raw'
set container name sing-box allow-host-networks
set container name sing-box volume config destination '/etc/sing-box'
set container name sing-box volume config source '/config/sing-box/'
set container name sing-box arguments 'run -D /etc/sing-box/'
set container name sing-box restart 'on-failure'
```

## 11. Finalize
```bash
# Pull image and save configuration
add container image ghcr.io/sagernet/sing-box:latest
commit
save
exit
```

### Note: Manual Image Load
```bash
# If automatic pull fails
podman pull docker.io/metacubex/mihomo:latest
podman save -o mihomo.tar metacubex/mihomo:latest
scp mihomo.tar vyos:/tmp/
sudo podman load -i /tmp/mihomo.tar
```