#!/usr/bin/dash
MIRRORLIST_PATH="/etc/pacman.d/mirrorlist"
# Check if reflector is installed
if ! command -v reflector >/dev/null 2>&1; then
	echo "reflector is not installed, installing..."
	sudo pacman -S --noconfirm reflector
fi
# Run reflector to find and save the fastest mirrors
if sudo reflector \
	-c China \
	-a 12 \
	-p https \
	--score 5 \
	--sort rate \
	-n 3 \
	--ipv4 \
	--save "$MIRRORLIST_PATH" >/dev/null 2>&1; then

	echo "Done. The new mirror list is:"
	cat "$MIRRORLIST_PATH"
else
	echo "Error: reflector command failed." >&2
	exit 1
fi
