#!/usr/bin/bash

IP="10.0.0.15"
MAC="00:23:24:67:DF:14"
IFACE="enp0s31f6"
PASS="123"

run_rdp() {
	xfreerdp3 /v:"$IP" /u:huai /p:"$PASS" /cert:ignore /sound /w:1916 /h:1056 >/dev/null 2>&1 &
	exit 0
}

check_online() {
	sudo arping -c 1 -w 1 -q -I "$IFACE" "$IP" >/dev/null 2>&1
}

# 1. 检查是否已在线，是则直接连接
check_online && run_rdp

# 2. 不在线则发送唤醒包
wakeonlan -i 10.0.0.255 "$MAC" >/dev/null 2>&1 || exit 1

# 3. 循环检测等待上线 (最多 15 秒)
i=0
while [ $i -lt 15 ]; do
	check_online && run_rdp
	sleep 1
	i=$((i + 1))
done

# 4. 超时无响应，静默退出
exit 1
