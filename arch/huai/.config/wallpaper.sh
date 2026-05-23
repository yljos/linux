#!/usr/bin/env bash
#feh --bg-fill --randomize /home/huai/Pictures
# feh --bg-fill /home/huai/Pictures/1.jpg
xwallpaper --maximize "$(find /home/huai/Pictures -type f | shuf -n 1)"
