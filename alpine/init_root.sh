
# Setup minimal Xorg base environment and drivers
setup-xorg-base

# Install compilation toolchain and X11 development headers (for building suckless tools like dwm/st/dmenu)
apk add --no-cache git gcc make musl-dev libx11-dev libxinerama-dev libxft-dev xterm rsync

# Install monospace fonts, DejaVu fallbacks, and font configuration engine
apk add --no-cache font-hack font-dejavu font-noto-cjk fontconfig

# Install Intel Haswell graphics driver, Mesa Gallium DRI, and VA-API hardware acceleration stack
apk add --no-cache mesa-dri-gallium xf86-video-intel libva-intel-driver libva-utils

# Install PipeWire audio server, session manager, and compatibility layers
apk add --no-cache pipewire wireplumber pipewire-pulse pipewire-alsa

# Add user 'huai' to wheel group for administrative access
adduser huai wheel

# Add user 'huai' to hardware device groups for GPU, audio, and input access
adduser huai video
adduser huai audio
adduser huai input