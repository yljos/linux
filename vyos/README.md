# VyOS 2025.11 Configuration Notes

## 1. Install
```bash
install image
```

## 2. Base Config
```bash
configure

# 配置 LAN 接口
set interfaces ethernet eth0 address 10.0.0.1/24
set interfaces ethernet eth0 description LAN

# DHCP 服务器
set service dhcp-server shared-network-name LAN authoritative
set service dhcp-server shared-network-name LAN option ntp-server 10.0.0.1
set service dhcp-server shared-network-name LAN option time-zone Asia/Shanghai
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 subnet-id 1

set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 option default-router 10.0.0.1
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 option name-server 10.0.0.1
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 range 0 start 10.0.0.101
set service dhcp-server shared-network-name LAN subnet 10.0.0.0/24 range 0 stop 10.0.0.200

# 配置 PPPoE 拨号 (绑定在 eth1)
set interfaces ethernet eth1 description WAN
set interfaces pppoe pppoe0 source-interface eth1
set interfaces pppoe pppoe0 authentication username 你的宽带账号
set interfaces pppoe pppoe0 authentication password 你的宽带密码
set interfaces pppoe pppoe0 mtu 1492
# 自动设置 MSS 钳制，防止大包无法传输
set interfaces pppoe pppoe0 ip adjust-mss clamp-mss-to-pmtu

# 源地址转换 (Masquerade)
set nat source rule 100 outbound-interface name pppoe0
set nat source rule 100 source address 10.0.0.0/24
set nat source rule 100 translation address masquerade

# DNS 转发服务
set system name-server pppoe0
set service dns forwarding cache-size 0
set service dns forwarding allow-from 10.0.0.0/24
set service dns forwarding system
# 删除现有的 LAN 监听地址，让它只在环回地址监听（不影响 sing-box 绑定 10.0.0.1）
delete service dns forwarding listen-address 10.0.0.1
set service dns forwarding listen-address 127.0.0.1

# SSH 服务
set service ssh listen-address 10.0.0.1
set system login user vyos authentication public-keys admin type ssh-ed25519
set system login user vyos authentication public-keys admin key AAAAC3NzaC1lZDI1NTE5AAAAIJiWQNpWDw/+0lhI1KeGL1MI0MiHhQ2HYe/qhjmddGni

# NTP 时间同步
set system time-zone UTC
set service ntp server ntp.aliyun.com
delete service ntp server time1.vyos.net
delete service ntp server time2.vyos.net
delete service ntp server time3.vyos.net
```

## 3. Firewall Config
```bash
# WAN 到内网：只允许已建立的回程流量
set firewall ipv4 name WAN-LAN default-action drop
set firewall ipv4 name WAN-LAN rule 1 action accept
set firewall ipv4 name WAN-LAN rule 1 state established
set firewall ipv4 name WAN-LAN rule 1 state related

# WAN 到路由器自身
set firewall ipv4 name WAN-LOCAL default-action drop
set firewall ipv4 name WAN-LOCAL rule 1 action accept
set firewall ipv4 name WAN-LOCAL rule 1 state established
set firewall ipv4 name WAN-LOCAL rule 1 state related

# 内部区域：默认信任（也可按需收紧）
set firewall ipv4 name LAN-WAN default-action accept
set firewall ipv4 name LAN-LOCAL default-action accept
set firewall ipv4 name LOCAL-LAN default-action accept
set firewall ipv4 name LOCAL-WAN default-action accept

# 定义 LOCAL 区域
set firewall zone LOCAL local-zone
set firewall zone LOCAL default-action drop
set firewall zone LOCAL from LAN firewall name LAN-LOCAL
set firewall zone LOCAL from WAN firewall name WAN-LOCAL

# 定义 LAN 区域
set firewall zone LAN member interface eth0
set firewall zone LAN default-action drop
set firewall zone LAN from LOCAL firewall name LOCAL-LAN
set firewall zone LAN from WAN firewall name WAN-LAN

# 定义 WAN 区域
set firewall zone WAN member interface pppoe0
set firewall zone WAN default-action drop
set firewall zone WAN from LAN firewall name LAN-WAN
set firewall zone WAN from LOCAL firewall name LOCAL-WAN
```

## 4. TProxy (Containers)
```bash
configure

# ==========================================
# 配置 Mihomo 容器
# ==========================================
# 1. 设置镜像 (使用拉取成功的 docker.io 源)
set container name mihomo image 'docker.io/metacubex/mihomo:latest'

# 2. 权限设置 (TUN/TProxy 模式必需)
set container name mihomo capability 'net-admin'
set container name mihomo capability 'net-raw'

# 3. 网络设置 (使用宿主机网络)
set container name mihomo allow-host-networks

# 4. 挂载配置文件 (建议将宿主机的 /config/mihomo/ 映射进去)
set container name mihomo volume config destination '/root/.config/mihomo'
set container name mihomo volume config source '/config/mihomo/'

# 5. 重启策略
set container name mihomo restart 'on-failure'
# 如果需要手动指定启动命令 (可选，通常镜像自带默认命令)
# set container name mihomo command '-d /root/.config/mihomo'

# ==========================================
# 配置 Sing-box 容器
# ==========================================
# 1. 设置镜像
set container name sing-box image 'ghcr.io/sagernet/sing-box:latest'

# 2. 权限设置 (TUN/TProxy 模式必需)
set container name sing-box capability 'net-admin'
set container name sing-box capability 'net-raw'

# 3. 网络设置 (使用宿主机网络)
set container name sing-box allow-host-networks

# 4. 挂载配置文件 (sing-box 默认寻找 /etc/sing-box/ 目录下的配置)
set container name sing-box volume config destination '/etc/sing-box'
set container name sing-box volume config source '/config/sing-box/'

# 5. 设置运行参数 (指定运行模式及配置文件路径)
set container name sing-box arguments 'run -D /etc/sing-box/'

# 6. 重启策略
set container name sing-box restart 'on-failure'

# ==========================================
# 预拉取镜像并保存
# ==========================================
add container image ghcr.io/sagernet/sing-box:latest

commit
save
exit
```

### Note: 容器拉取失败的备用方案
```bash
# 若 add container image 拉取失败，可在本地终端或 VyOS 底层手动离线导入：
podman pull docker.io/metacubex/mihomo:latest
podman save -o mihomo.tar metacubex/mihomo:latest
scp mihomo.tar vyos:/tmp/

# 登入 VyOS 执行离线加载
sudo podman load -i /tmp/mihomo.tar

# 对应的 VyOS 手动拉取命令声明
add container image docker.io/metacubex/mihomo:latest
```