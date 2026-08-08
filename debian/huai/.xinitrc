#!/usr/bin/env bash

# 1. Instant execution of system-level background processes
numlockx &
pidof -q picom || picom -b
pidof -q dunst || dunst &

[[ -f /home/huai/.config/wallpaper.sh ]] && /bin/bash /home/huai/.config/wallpaper.sh
[[ -f /home/huai/.config/status.sh ]] && /bin/bash /home/huai/.config/status.sh &

# 2. Place time-consuming or GUI autostarts in a background subshell to avoid blocking dwm
(
    sleep 2  # Wait for dwm and network to be fully ready
    pidof -q firefox || firefox &    
) &
xset s off -dpms
# 3. Instantly start the window manager
exec dbus-run-session dwm