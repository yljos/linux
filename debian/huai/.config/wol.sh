#!/usr/bin/env bash

wakeonlan -i "10.0.0.255" "00:23:24:67:DF:14" >/dev/null 2>&1
notify-send "WOL" "唤醒魔术包已发送"
