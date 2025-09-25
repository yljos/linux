#!/bin/sh

# Cloudflared metrics 端口
METRICS_PORT=12138

# 获取隧道活跃连接数
CONNECTED=$(curl -s http://127.0.0.1:$METRICS_PORT/metrics | grep '^cloudflared_tunnel_ha_connections' | awk '{print $2}')

# 判断是否连通
if [ "$CONNECTED" -eq 0 ]; then
	echo "$(date): cloudflared 隧道未连接，重启服务器" >>/var/log/cloudflared-monitor.log
	/usr/bin/systemctl reboot
fi
