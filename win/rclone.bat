@echo off
setlocal
:: ================= Configuration =================
:: Using corrected paths [cite: 2026-02-02]
set RCLONE_EXE="C:\rclone-v1.71.0-windows-amd64\rclone.exe"
set CONF="%AppData%\rclone\rclone.conf"

:: Remote control ports [cite: 2026-01-27]
set NAS_RC=127.0.0.1:5572
set PIK_RC=127.0.0.1:5573
:: =================================================

:MENU
cls
echo ==========================================
echo       Rclone Minimalist Manager
echo ==========================================
echo  1. Mount PikPak (P:)
echo  2. Mount NAS    (Z:)
echo  3. Unmount PikPak
echo  4. Unmount NAS
echo  0. Exit
echo ==========================================
set /p choice="Select (0-4): "

if "%choice%"=="1" goto MOUNT_PIK
if "%choice%"=="2" goto MOUNT_NAS
if "%choice%"=="3" goto UNMOUNT_PIK
if "%choice%"=="4" goto UNMOUNT_NAS
if "%choice%"=="0" exit
goto MENU

:MOUNT_PIK
echo [PikPak] Mounting...
start "" %RCLONE_EXE% mount pikpak: P: --config %CONF% --vfs-cache-mode full --vfs-cache-max-size 10G --network-mode --no-console --rc --rc-no-auth --rc-addr %PIK_RC% --no-modtime --no-checksum
goto DONE

:MOUNT_NAS
echo [NAS] Mounting...
start "" %RCLONE_EXE% mount nas:/data Z: --config %CONF% --vfs-cache-mode full --network-mode --vfs-links --no-console --rc --rc-no-auth --rc-addr %NAS_RC% --sftp-ciphers aes128-gcm@openssh.com
goto DONE

:UNMOUNT_PIK
echo [PikPak] Unmounting...
%RCLONE_EXE% rc core/quit --rc-addr %PIK_RC%
goto DONE

:UNMOUNT_NAS
echo [NAS] Unmounting...
%RCLONE_EXE% rc core/quit --rc-addr %NAS_RC%
goto DONE

:DONE
echo Done.
timeout /t 1 >nul
goto MENU