# VyOS 2025.11 Configuration Notes

## 1. Install
```bash
# Enter image installation mode
install image
```

## 2. Base Connectivity

### 2.1 PPPoE Credentials
```bash
configure
```
```bash
set interfaces pppoe pppoe0 authentication username 'YOUR_USERNAME'
```

```bash
set interfaces pppoe pppoe0 authentication password 'YOUR_PASSWORD'
```

### 2.2 Enter Configuration Mode
```bash
configure
```

### 2.3 lan Interface
```bash
# Define lan interface
set interfaces ethernet eth0 address 10.0.0.1/24
set interfaces ethernet eth0 description lan
```

### 2.4 PPPoE Interface Binding
```bash
# Bind PPPoE to physical interface eth1
set interfaces ethernet eth1 description wan
set interfaces pppoe pppoe0 source-interface eth1
```

### 2.5 PPPoE MTU & MSS Optimization
```bash
# Optimize for PPPoE stability
set interfaces pppoe pppoe0 mtu 1492
set interfaces pppoe pppoe0 ip adjust-mss clamp-mss-to-pmtu
```

## 3. DHCP Server
```bash
# Configure DHCP for lan
set service dhcp-server shared-network-name lan authoritative
set service dhcp-server shared-network-name lan option ntp-server 10.0.0.1
set service dhcp-server shared-network-name lan option time-zone UTC
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 subnet-id 1
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 option default-router 10.0.0.1
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 option name-server 10.0.0.1
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 range 0 start 10.0.0.101
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 range 0 stop 10.0.0.200
```
```bash
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 static-mapping void ip-address 
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 static-mapping void mac 
set service dhcp-server shared-network-name lan subnet 10.0.0.0/24 ignore-client-id

```

## 4. DNS Forwarding

### 4.1 Global Settings
```bash
# DNS forwarding settings
set system name-server pppoe0
set service dns forwarding cache-size 0
set service dns forwarding allow-from 10.0.0.0/24
set service dns forwarding system
```

### 4.2 Listen Address
```bash
# Listen on loopback only (ensures port 53 is free for sing-box on 10.0.0.1)
delete service dns forwarding listen-address 10.0.0.1
set service dns forwarding listen-address 127.0.0.1
```

## 5. SSH Service
```bash
# SSH Access and Public Key
set service ssh listen-address 10.0.0.1
set system login user vyos authentication public-keys admin type ssh-ed25519
set system login user vyos authentication public-keys admin key AAAAC3NzaC1lZDI1NTE5AAAAINM0X4WA7BeuGIYKJMjQ/WbewIFlS0140P66A8Ntbsex
```

## 6. NTP & Timezone
```bash
# Time synchronization and UTC zone
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

## 8. Firewall Rulesets

### 8.1 wan to lan
```bash
# Drop unsolicited traffic from wan
set firewall ipv4 name wan-lan default-action drop
set firewall ipv4 name wan-lan rule 1 action accept
set firewall ipv4 name wan-lan rule 1 state established
set firewall ipv4 name wan-lan rule 1 state related
```

### 8.2 wan to local
```bash
# Protect router itself from wan
set firewall ipv4 name wan-local default-action drop
set firewall ipv4 name wan-local rule 1 action accept
set firewall ipv4 name wan-local rule 1 state established
set firewall ipv4 name wan-local rule 1 state related
```

### 8.3 Internal Traffic
```bash
# Trust internal network flows
set firewall ipv4 name lan-wan default-action accept
set firewall ipv4 name lan-local default-action accept
set firewall ipv4 name local-lan default-action accept
set firewall ipv4 name local-wan default-action accept
```

## 9. Firewall Zones

### 9.1 local Zone
```bash
# Policy for the router itself
set firewall zone local local-zone
set firewall zone local default-action drop
set firewall zone local from lan firewall name lan-local
set firewall zone local from wan firewall name wan-local
```

### 9.2 lan Zone
```bash
# Policy for lan interface
set firewall zone lan member interface eth0
set firewall zone lan default-action drop
set firewall zone lan from local firewall name local-lan
set firewall zone lan from wan firewall name wan-lan
```

### 9.3 wan Zone
```bash
# Policy for PPPoE interface
set firewall zone wan member interface pppoe0
set firewall zone wan default-action drop
set firewall zone wan from lan firewall name lan-wan
set firewall zone wan from local firewall name local-wan
```

## 10. Containers (TProxy)

### 10.1 Mihomo
```bash
# Setup Mihomo container
set container name mihomo image 'docker.io/metacubex/mihomo:latest'
set container name mihomo capability 'net-admin'
set container name mihomo capability 'net-raw'
set container name mihomo allow-host-networks
set container name mihomo volume config destination '/root/.config/mihomo'
set container name mihomo volume config source '/config/mihomo/'
set container name mihomo restart 'on-failure'
```

### 10.2 Sing-box
```bash
# Setup Sing-box container
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
# Pull images and save changes
add container image ghcr.io/sagernet/sing-box:latest
commit
save
exit
```

### Note: Manual Image Load
```bash
# In case of automatic pull failure
podman pull docker.io/metacubex/mihomo:latest
podman save -o mihomo.tar metacubex/mihomo:latest
mv mihomo.tar /data/www
```
```bash
scp mihomo.tar vyos:/tmp/
```
```bash
sudo podman load -i /tmp/mihomo.tar
```