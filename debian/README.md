# Update package list and install minimal Xorg, build tools, dependencies, and vim
sudo apt update
sudo apt install --no-install-recommends xserver-xorg-core xserver-xorg-input-all xserver-xorg-video-all xinit build-essential libx11-dev libxft-dev libxinerama-dev git vim ca-certificates

# Install open-source Noto CJK fonts
sudo apt install fonts-noto-cjk

# Update font cache
fc-cache -fv