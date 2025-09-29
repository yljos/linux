#!/usr/bin/env bash

play ~/.config/dunst/xp.wav &

if ! pgrep -x "firefox" &>/dev/null; then
	firefox &
fi

if ! pgrep -x "Telegram" &>/dev/null; then
	Telegram &
fi

if [ -f ~/.config/wallpaperautochange.sh ] && ! pgrep -f "bash.*wallpaperautochange.sh" &>/dev/null; then
	/bin/bash ~/.config/wallpaperautochange.sh &
fi

if [ -f ~/.config/shutdown.sh ] && ! pgrep -f "bash.*shutdown.sh" &>/dev/null; then
	/bin/bash ~/.config/shutdown.sh &
fi

if command -v numlockx &>/dev/null; then
	numlockx &
fi

if ! pgrep -x "picom" &>/dev/null; then
	picom -b
fi

if ! pgrep -x "fcitx5" &>/dev/null; then
	fcitx5 -d
fi

if ! pgrep -x "dunst" &>/dev/null; then
	dunst &
fi

sleep 3

if [ -f ~/.config/dwm/dwm_status.sh ] && ! pgrep -f "bash.*dwm_status.sh" &>/dev/null; then
	/bin/bash ~/.config/dwm/dwm_status.sh &
fi
