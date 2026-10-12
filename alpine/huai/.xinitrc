
# Disable screen saver and DPMS blanking
xset s off -dpms

# Start PipeWire core daemon
pipewire &

# Give pipewire socket a moment to initialize before session manager and pulse layer
sleep 1
wireplumber &
pipewire-pulse &

"$HOME/.config/status.sh" &

# Execute dwm window manager
exec dwm