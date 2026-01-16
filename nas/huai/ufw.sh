#!/usr/bin/env bash

# 重置防火墙规则
sudo ufw reset

# SSH 访问
sudo ufw allow proto tcp to any port 22

# Samba UDP 端口
sudo ufw allow proto udp to any port 137
sudo ufw allow proto udp to any port 138

# Samba TCP 端口
sudo ufw allow proto tcp to any port 139
sudo ufw allow proto tcp to any port 445

# Docker/Podman 网络
sudo ufw allow in on podman0

# HTTP 和 HTTPS 端口
sudo ufw allow proto tcp to any port 80   # HTTP
sudo ufw allow proto tcp to any port 8080 # HTTP
# sudo ufw allow proto tcp to any port 8443 # HTTPS
sudo ufw allow proto tcp to any port 8088 # HTTP

# NFSv4 端口
sudo ufw allow proto tcp from 10.0.0.25 to any port 2049 # NFSv4 主端口

# Podman 容器 TCP 端口
sudo ufw allow proto tcp to any port 8096 # jellyfin server
sudo ufw allow proto tcp to any port 6800 # aria2-pro
sudo ufw allow proto tcp to any port 6888 # aria2-pro
sudo ufw allow proto tcp to any port 6880 # ariang
sudo ufw allow proto tcp to any port 5008 # shutdown
sudo ufw allow proto tcp to any port 8083 # calibre-web
sudo ufw allow proto tcp to any port 4000 # tinymediamanager
sudo ufw allow proto tcp to any port 5900 # tinymediamanager VNC
sudo ufw allow proto tcp to any port 8181 # vaultwarden

sudo ufw allow proto tcp to any port 8002 # music-tag-web
sudo ufw allow proto tcp to any port 3000 # homepage
sudo ufw allow proto tcp to any port 3001 # gitea
sudo ufw allow proto tcp to any port 2222 # gitea_ssh
sudo ufw allow proto tcp to any port 8123 # homeassistant
sudo ufw allow proto tcp to any port 6065 # webdav-server
sudo ufw allow proto tcp to any port 8081 # calibre
# Podman 容器 UDP 端口
sudo ufw allow proto udp to any port 1900 # homeassistant
sudo ufw allow proto udp to any port 5353 # homeassistant
sudo ufw allow proto udp to any port 6888 # aria2-pro
