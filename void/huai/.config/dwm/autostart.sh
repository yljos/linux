#!/usr/bin/env bash

sleep 0.5
mpv --no-video /home/huai/.config/dunst/xp.wav &

command -v numlockx &>/dev/null && numlockx &
# ! pgrep -x "picom" &>/dev/null && picom -b
# ! pgrep -x "fcitx5" &>/dev/null && fcitx5 -d
! pgrep -x "dunst" &>/dev/null && dunst &

# [[ -f /home/huai/.config/wallpaperchange.sh ]] && /bin/bash /home/huai/.config/wallpaperchange.sh
[[ -f /home/huai/.config/dwm/dwm_status.sh ]] && /bin/bash /home/huai/.config/dwm/dwm_status.sh &


sleep 1
# ! pgrep -f "librewolf" &>/dev/null && librewolf &
# ! pgrep -x "Telegram" &>/dev/null && Telegram &
