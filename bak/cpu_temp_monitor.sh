#!/usr/bin/env bash
THRESHOLD=30
TEMPERATURE=$(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')

# 使用整数比较
if [ "$TEMPERATURE" -gt "$THRESHOLD" ]; then
	MESSAGE="🔴 警告！TrueNas CPU温度达到了 $TEMPERATURE °C！"
	curl -s -X POST "https://api.telegram.org/bot /sendMessage" -d "chat_id= &text=$MESSAGE&parse_mode=HTML"
fi
