#!/usr/bin/sh
# 后台运行整个脚本逻辑
(
    # 目标主机信息
    TARGET_HOST="pve"
    MAC_ADDRESS="00:23:24:67:DF:14"
    INTERFACE="enp0s31f6"

    # 检查必要命令是否安装
    for cmd in arping wakeonlan notify-send; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            notify-send "错误" "$cmd 未安装"
            exit 1
        fi
    done

    # 获取主机IP
    TARGET_IP=$(getent hosts "$TARGET_HOST" | awk '{ print $1 }')
    if [ -z "$TARGET_IP" ]; then
        notify-send "错误" "无法解析主机名"
        exit 1
    fi

    # 检查主机是否在线
    if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
        notify-send "PVE主机已在线" && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
    else
        notify-send "唤醒中" "发送WOL包..." && play ~/.config/dunst/wol.mp3 >/dev/null 2>&1
        if wakeonlan "$MAC_ADDRESS" >/dev/null 2>&1; then
            notify-send "已发送唤醒" "正在检测是否上线..." && play ~/.config/dunst/starting.mp3 >/dev/null 2>&1
            MAX_TRIES=20
            i=1
            while [ $i -le $MAX_TRIES ]; do
                if sudo arping -c 1 -w 1 -q -I "$INTERFACE" "$TARGET_IP" >/dev/null 2>&1; then
                    notify-send "PVE主机已上线" && play ~/.config/dunst/system_online.mp3 >/dev/null 2>&1
                    break
                fi
                # 每2次（2秒）显示一次进度
                if [ $((i % 2)) -eq 0 ]; then
                    notify-send "检测中" "$i/20 秒"
                fi
                sleep 1
                i=$((i + 1))
            done
            if [ $i -gt $MAX_TRIES ]; then
                notify-send "主机未上线" "请稍后手动重试" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
            fi
        else
            notify-send "唤醒失败" "请检查网络连接" && play ~/.config/dunst/error.mp3 >/dev/null 2>&1
            exit 1
        fi
    fi
) >/dev/null 2>&1 &

