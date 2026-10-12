## dwm
sudo xbps-install -Su base-devel libX11-devel libXft-devel libXinerama-devel git xinit xorg vim curl font-hack-ttf noto-fonts-ttf noto-fonts-cjk -y
sudo xbps-install -Su dbus font-misc-misc -y 

## 
sudo xbps-install -Su rsync rofi alacritty gnupg -y
## dri
sudo xbps-install -Su intel-media-driver mpv ffmpeg -y
## nfs
sudo xbps-install -Su nfs-utils -y
## pipewire
sudo xbps-install -S pipewire wireplumber -y
