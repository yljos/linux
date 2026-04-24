@echo off
setlocal

:: Configuration
set CONF="%AppData%\rclone\rclone.conf"
set PIK_RC=127.0.0.1:5573

:: Mount PikPak
start "" rclone mount pikpak: P: --config %CONF% --vfs-cache-mode full --vfs-cache-max-size 10G --network-mode --no-console --rc --rc-no-auth --rc-addr %PIK_RC% --no-modtime --no-checksum

:: Unmount PikPak
rclone rc core/quit --rc-addr %PIK_RC%

exit