@echo off
setlocal

:: Configuration
set RCLONE_EXE="C:\rclone-v1.73.3-windows-amd64\rclone.exe"
set CONF="%AppData%\rclone\rclone.conf"
set NAS_RC=127.0.0.1:5572
set PIK_RC=127.0.0.1:5573

cls
echo 1. Mount PikPak (P:)
echo 2. Mount NAS    (Z:)
echo 3. Unmount PikPak
echo 4. Unmount NAS
echo 0. Exit
set /p choice="Select (0-4): "

if "%choice%"=="1" start "" %RCLONE_EXE% mount pikpak: P: --config %CONF% --vfs-cache-mode full --vfs-cache-max-size 10G --network-mode --no-console --rc --rc-no-auth --rc-addr %PIK_RC% --no-modtime --no-checksum
if "%choice%"=="2" start "" %RCLONE_EXE% mount nas:/data Z: --config %CONF% --vfs-cache-mode full --network-mode --vfs-links --no-console --rc --rc-no-auth --rc-addr %NAS_RC% --sftp-ciphers aes128-gcm@openssh.com
if "%choice%"=="3" %RCLONE_EXE% rc core/quit --rc-addr %PIK_RC%
if "%choice%"=="4" %RCLONE_EXE% rc core/quit --rc-addr %NAS_RC%

:: Auto exit after one execution
exit