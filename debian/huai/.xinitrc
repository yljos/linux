#!/usr/bin/env bash

# 1. Initialize D-Bus session early so all background processes can use it
eval "$(dbus-launch --sh-syntax --exit-with-session)"

# 2. Export environment variables
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx

# 3. Instant execution of system-level background processes
numlockx &
pidof -q picom || picom -b
pidof -q dunst || dunst &
fcitx5 -d &

# [[ -f /home/huai/.config/wallpaper.sh ]] && /bin/bash /home/huai/.config/wallpaper.sh
[[ -f /home/huai/.config/status.sh ]] && /bin/bash /home/huai/.config/status.sh &

# 4. Place time-consuming or GUI autostarts in a background subshell
(
    sleep 2  # Wait for dwm and network to be fully ready
    pidof -q librewolf || librewolf &    
) &

xset s off

# 5. Instantly start the window manager (dbus is already running)
exec dwm
