# dwl
sudo apt install  build-essential pkg-config libwlroots-0.18-dev libwayland-dev libxkbcommon-dev libinput-dev libxcb1-dev libxcb-icccm4-dev wayland-protocols
sudo apt install libfcft-dev libpixman-1-dev    
# dwm
sudo apt install build-essential libx11-dev libxinerama-dev libxft-dev
sudo apt install xserver-xorg xinit
sudo apt install freerdp3-x11
xfreerdp /v:IP地址 /u:用户名 /p:密码 /f /sound /clipboard /dynamic-resolution
# 
apt update && apt install sudo
usermod -aG sudo huai
apt install git curl vim  
apt install pipewire pipewire-pulse pipewire-alsa wireplumber
systemctl --user --now enable pipewire pipewire-pulse wireplumber