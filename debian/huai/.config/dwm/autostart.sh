#!/usr/bin/env bash

mpv --no-video /home/huai/.config/dunst/xp.wav &

if ! pgrep -f "firefox" &>/dev/null; then
	sleep 3
	firefox-esr &
fi

if ! pgrep -x "Telegram" &>/dev/null; then
	Telegram &
fi


if [ -f /home/huai/.config/shutdown.sh ]; then
	/bin/bash /home/huai/.config/shutdown.sh &
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

if [ -f /home/huai/.config/dwm/dwm_status.sh ] && ! pgrep -f "bash.*dwm_status.sh" &>/dev/null; then
	/bin/bash /home/huai/.config/dwm/dwm_status.sh &
fi
