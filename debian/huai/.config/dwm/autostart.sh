#!/usr/bin/env bash

sleep 0.5
[[ -f /home/huai/.config/dwm/dwm_status.sh ]] && /bin/bash /home/huai/.config/dwm/dwm_status.sh &
mpv --no-video /home/huai/.config/dunst/xp.wav &

[[ -f /home/huai/.config/shutdown.sh ]] && /bin/bash /home/huai/.config/shutdown.sh &
[[ -f /home/huai/.config/wallpaperchange.sh ]] && /bin/bash /home/huai/.config/wallpaperchange.sh

sleep 1
! pgrep -f "firefox" &>/dev/null && firefox-esr &
! pgrep -x "Telegram" &>/dev/null && Telegram &

command -v numlockx &>/dev/null && numlockx &
! pgrep -x "picom" &>/dev/null && picom -b
! pgrep -x "fcitx5" &>/dev/null && fcitx5 -d
sleep 10
! pgrep -x "dunst" &>/dev/null && dunst &