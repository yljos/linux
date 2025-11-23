#!/usr/bin/env python3
"""
DWL Status Bar Generator
优化版本：
1. 异步天气更新 (解决启动卡顿)
2. Socket 直连 MPD (极大降低 CPU 占用)
3. 精准时间对齐 (解决时间漂移，秒针跳动均匀)
"""

import os
import sys
import time
import signal
import subprocess
import threading
import socket  # 新增：用于 MPD 通信
from pathlib import Path
from datetime import datetime
import re

# =============================================================================
# --- CONFIGURATION ---
# =============================================================================

# --- 1. Icons ---
ICON_ARCH = "A:"
ICON_TEMP = "T:"
ICON_CPU = "C:"
ICON_MEM = "M:"
ICON_VOL = "V:"
ICON_BT = "B:"
ICON_NET_DOWN = "D:"
ICON_NET_UP = "U:"
ICON_WEATHER = "W:"

# --- 2. Colors ---
C_NORM = "^fg(00ff00)"
C_WARN = "^fg(ffff00)"
C_CRIT = "^fg(ff0000)"
C_BLUE = "^fg(66a3ff)"
C_RESET = "^fg()"

# --- 3. System Settings ---
CPU_TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"
INTERFACE = "enp0s31f6"
WEATHER_LOCATION = "" 
LOCATION_GPG = str(Path.home() / ".config" / "location.gpg")

# MPD 设置 (根据你的 mpd.conf)
MPD_HOST = '127.0.0.1'
MPD_PORT = 6600

def _try_load_location_from_gpg(timeout: int = 5):
    try:
        if not LOCATION_GPG or not os.path.isfile(LOCATION_GPG):
            return None
        res = subprocess.run(
            ["gpg", "--batch", "--yes", "-d", LOCATION_GPG],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        if res.returncode == 0 and res.stdout.strip():
            return os.path.expanduser(res.stdout.strip())
    except Exception:
        return None
    return None

# --- 4. Behavior Settings ---
UPDATE_INTERVAL_MEDIUM = 5
UPDATE_INTERVAL_LONG = 60
UPDATE_INTERVAL_WEATHER = 1800
SEPARATOR = "|"

# =============================================================================
# --- GLOBAL STATE ---
# =============================================================================

class StatusBar:
    def __init__(self):
        global WEATHER_LOCATION
        if not WEATHER_LOCATION and LOCATION_GPG:
            try:
                res = subprocess.run(
                    ["gpg", "--batch", "--yes", "-d", LOCATION_GPG],
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout.strip():
                    loc = res.stdout.strip()
                    loc = os.path.expanduser(loc)
                    WEATHER_LOCATION = loc
            except Exception:
                pass

        self.kernel_version = self._get_kernel_version()
        self.arch = f"{C_NORM}{self.kernel_version.split('-')[0]}{C_RESET}"

        self.net_rx_file = f"/sys/class/net/{INTERFACE}/statistics/rx_bytes"
        self.net_tx_file = f"/sys/class/net/{INTERFACE}/statistics/tx_bytes"
        self.rx1 = None
        self.tx1 = None
        self.net_status_str = ""

        if self._file_readable(self.net_rx_file):
            self.rx1 = int(open(self.net_rx_file).read().strip())
            self.tx1 = int(open(self.net_tx_file).read().strip())
        else:
            self.net_status_str = "N/A"

        self.prev_cpu = 0
        self.prev_idle = 0
        self._update_cpu_baseline()

        self.cpu_status = ""
        self.mem_status = ""
        self.temp_status = ""
        self.vol_status = ""
        self.music_status = ""
        self.ime_status = ""
        self.time_status = ""
        self.bluetooth_status = ""
        self.weather_status = ""

    def _get_kernel_version(self):
        try:
            return os.uname().release
        except:
            return "Unknown"

    def _file_readable(self, path):
        try:
            return os.access(path, os.R_OK)
        except:
            return False

    def _update_cpu_baseline(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline().split()
                cpu_user, cpu_nice, cpu_system, cpu_idle = (
                    int(line[1]), int(line[2]), int(line[3]), int(line[4])
                )
                cpu_iowait, cpu_irq, cpu_softirq = (
                    int(line[5]), int(line[6]), int(line[7])
                )
                self.prev_cpu = (
                    cpu_user + cpu_nice + cpu_system + cpu_idle +
                    cpu_iowait + cpu_irq + cpu_softirq
                )
                self.prev_idle = cpu_idle
        except:
            pass

    def update_cpu(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline().split()
                cpu_user, cpu_nice, cpu_system, cpu_idle = (
                    int(line[1]), int(line[2]), int(line[3]), int(line[4])
                )
                cpu_iowait, cpu_irq, cpu_softirq = (
                    int(line[5]), int(line[6]), int(line[7])
                )

                curr_cpu = (
                    cpu_user + cpu_nice + cpu_system + cpu_idle +
                    cpu_iowait + cpu_irq + cpu_softirq
                )
                curr_idle = cpu_idle
                total_diff = curr_cpu - self.prev_cpu
                idle_diff = curr_idle - self.prev_idle

                usage = 0
                if total_diff > 0:
                    usage = int(100 * (total_diff - idle_diff) / total_diff)

                self.prev_cpu = curr_cpu
                self.prev_idle = curr_idle

                if usage >= 90:
                    color_code = C_CRIT
                elif usage >= 75:
                    color_code = C_WARN
                else:
                    color_code = C_NORM

                self.cpu_status = f"{color_code}{usage:02d}%{C_RESET}"
        except:
            self.cpu_status = "N/A"

    def update_mem(self):
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    meminfo[parts[0].rstrip(":")] = int(parts[1])

                total_mb = meminfo.get("MemTotal", 0) / 1024
                available_mb = meminfo.get("MemAvailable", 0) / 1024
                used_mb = total_mb - available_mb

                self.mem_status = f"{int(used_mb)}/{int(total_mb)}MB"
        except:
            self.mem_status = "N/A"

    def update_temp(self):
        try:
            if os.path.isfile(CPU_TEMP_FILE) and os.access(CPU_TEMP_FILE, os.R_OK):
                with open(CPU_TEMP_FILE, "r") as f:
                    temp_val = int(int(f.read().strip()) / 1000)

                if temp_val >= 80:
                    color_code = C_CRIT
                elif temp_val >= 65:
                    color_code = C_WARN
                else:
                    color_code = C_NORM

                self.temp_status = f"{ICON_TEMP}{color_code}{temp_val}°C{C_RESET}"
            else:
                self.temp_status = f"{ICON_TEMP}N/A"
        except:
            self.temp_status = f"{ICON_TEMP}N/A"

    def update_bluetooth(self):
        self.bluetooth_status = ""
        try:
            subprocess.run(
                ["pgrep", "-x", "bluetoothd"], capture_output=True, check=True
            )
        except:
            return

        try:
            result = subprocess.run(
                ["bluetoothctl", "info"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "Battery Percentage" in line:
                    match = re.search(r"\((\d+)%\)", line)
                    if match:
                        level = int(match.group(1))
                        if level <= 20:
                            color_code = C_CRIT
                        elif level <= 30:
                            color_code = C_WARN
                        else:
                            color_code = C_NORM
                        self.bluetooth_status = f"{ICON_BT}{color_code}{level}%{C_RESET}"
                        break
        except:
            pass

    def update_volume(self):
        try:
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True,
                text=True,
            )
            match = re.search(r"(\d+)%", result.stdout)
            if match:
                vol = int(match.group(1))
            else:
                vol = 50
            self.vol_status = f"{vol:02d}%"
        except:
            self.vol_status = "50%"

    def update_music(self):
        """
        [优化2] 使用 Socket 连接 MPD
        替代 subprocess.run(['mpc'])，减少进程创建开销，速度更快
        """
        try:
            # 连接 MPD
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2) # 设置短超时，防止阻塞
                s.connect((MPD_HOST, MPD_PORT))
                
                # 发送查询命令 (currentsong 获取信息, status 获取状态)
                s.send(b"currentsong\nstatus\nclose\n")
                
                # 接收数据
                data = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                
                response = data.decode('utf-8', errors='ignore')
                
                # 解析数据
                state = "stop"
                artist = ""
                title = ""
                name = ""
                
                for line in response.splitlines():
                    if line.startswith('state: '):
                        state = line.replace('state: ', '').strip()
                    elif line.startswith('Artist: '):
                        artist = line.replace('Artist: ', '').strip()
                    elif line.startswith('Title: '):
                        title = line.replace('Title: ', '').strip()
                    elif line.startswith('Name: '):
                        name = line.replace('Name: ', '').strip()

                if state == 'play':
                    # 优先显示 Artist - Title，其次显示 Title，最后显示 Name (电台名)
                    if artist and title:
                        display = f"{artist} - {title}"
                    elif title:
                        display = title
                    elif name:
                        display = name
                    else:
                        display = "Unknown"
                        
                    self.music_status = f"{C_NORM}{display}{C_RESET}"
                else:
                    self.music_status = ""
                    
        except (socket.error, socket.timeout, ConnectionRefusedError):
            # 连接失败 (MPD 未运行或配置错误) 清空状态
            self.music_status = ""
        except Exception:
            self.music_status = ""

    def update_ime(self):
        try:
            result = subprocess.run(
                ["fcitx5-remote"], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip() == "2":
                self.ime_status = f"{C_WARN}CN{C_RESET}"
            else:
                self.ime_status = f"{C_NORM}EN{C_RESET}"
        except:
            self.ime_status = f"{C_NORM}EN{C_RESET}"

    def update_time(self):
        self.time_status = datetime.now().strftime("%Y-%m-%d %H:%M %a")

    def update_weather_async(self):
        thread = threading.Thread(target=self.update_weather)
        thread.daemon = True
        thread.start()

    def update_weather(self):
        try:
            global WEATHER_LOCATION
            location = WEATHER_LOCATION or ""
            if not location:
                loc = _try_load_location_from_gpg()
                if loc:
                    WEATHER_LOCATION = loc
                    location = WEATHER_LOCATION
            url = f"wttr.in/{location}?format=%t+%C"

            result = subprocess.run(
                ["curl", "-s", "-m", "10", url],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0 and result.stdout.strip():
                weather = result.stdout.strip()
                lw = weather.lower()

                temp_match = re.search(r"([+-]?\d+\s*°?C?)", weather)
                temp_str = None
                if temp_match:
                    temp_str = temp_match.group(1).strip()

                temp_color = C_NORM
                if temp_str:
                    num_match = re.search(r"([+-]?\d+)", temp_str)
                    if num_match:
                        try:
                            t = int(num_match.group(1))
                            if t <= 10:
                                temp_color = C_CRIT
                            elif t < 18:
                                temp_color = C_BLUE
                            elif t <= 26:
                                temp_color = C_NORM
                            elif t <= 32:
                                temp_color = C_WARN
                            else:
                                temp_color = C_CRIT
                        except Exception:
                            temp_color = C_NORM

                cond_str = weather
                if temp_str:
                    cond_str = weather.replace(temp_str, "", 1).strip()

                cond_color = C_NORM
                if any(k in lw for k in ("tornado", "hurricane", "storm")):
                    cond_color = C_CRIT
                elif any(k in lw for k in ("rain", "shower", "ice")):
                    cond_color = C_BLUE
                elif any(k in lw for k in ("mist", "fog")):
                    cond_color = C_BLUE
                
                if temp_str:
                    self.weather_status = f"{ICON_WEATHER}{temp_color}{temp_str}{C_RESET} {cond_color}{cond_str}{C_RESET}"
                else:
                    self.weather_status = f"{ICON_WEATHER}{cond_color}{weather}{C_RESET}"
            else:
                self.weather_status = f"{ICON_WEATHER}N/A"
        except:
            self.weather_status = f"{ICON_WEATHER}N/A"

    def update_net(self):
        if self.rx1 is None:
            self.net_status_str = self.net_status_str or "N/A"
            return
        try:
            rx2 = int(open(self.net_rx_file).read().strip())
            tx2 = int(open(self.net_tx_file).read().strip())
            rx_diff = rx2 - self.rx1
            tx_diff = tx2 - self.tx1
            self.rx1 = rx2
            self.tx1 = tx2
            rx_mbps = (rx_diff * 8) // 1000000
            tx_mbps = (tx_diff * 8) // 1000000
            self.net_status_str = f"{ICON_NET_DOWN}{rx_mbps}Mbps {ICON_NET_UP}{tx_mbps}Mbps"
        except:
            self.net_status_str = "N/A"

    def print_status_bar(self):
        parts = []
        parts.append(f"{ICON_ARCH}{self.arch}")
        if self.music_status:
            parts.append(self.music_status)
        parts.append(self.temp_status)
        parts.append(f"{ICON_CPU}{self.cpu_status}")
        parts.append(f"{ICON_MEM}{self.mem_status}")
        if self.bluetooth_status:
            parts.append(self.bluetooth_status)
        parts.append(f"{ICON_VOL}{self.vol_status}")
        parts.append(self.net_status_str)
        if self.weather_status:
            parts.append(self.weather_status)
        parts.append(self.time_status)
        parts.append(self.ime_status)
        
        print(SEPARATOR.join(parts))
        sys.stdout.flush()

# =============================================================================
# --- MAIN EXECUTION ---
# =============================================================================

def main():
    status = StatusBar()

    def handle_volume_change(signum, frame):
        status.update_volume()
        status.print_status_bar()

    def handle_ime_change(signum, frame):
        status.update_ime()
        status.print_status_bar()

    def handle_pipe_signal(signum, frame):
        sys.exit(0)

    signal.signal(signal.SIGUSR1, handle_volume_change)
    signal.signal(signal.SIGUSR2, handle_ime_change)
    signal.signal(signal.SIGPIPE, handle_pipe_signal)

    # 首次运行
    status.update_cpu()
    status.update_mem()
    status.update_temp()
    status.update_music() # 使用新的 Socket 方法
    status.update_ime()
    status.update_time()
    status.update_net()
    status.update_volume()
    status.update_bluetooth()
    status.update_weather_async()

    # 主循环
    try:
        while True:
            # 记录循环开始时间，用于精准计算休眠时间
            start_time = time.time()
            current_sec = int(start_time)
            
            # --- 高频更新 (每秒) ---
            status.update_cpu()
            status.update_temp()
            status.update_net()
            status.update_time() # 时间最好每秒刷，保证切换分钟时即时显示

            # --- 中频更新 ---
            if current_sec % UPDATE_INTERVAL_MEDIUM == 0:
                status.update_mem()
                status.update_music() # Socket 方式开销极小
                status.update_bluetooth()

            # --- 低频更新 (天气) ---
            if current_sec % UPDATE_INTERVAL_WEATHER == 0:
                status.update_weather_async()

            status.print_status_bar()

            # [优化1] 精准时间对齐
            # 计算距离下一秒整点还有多少微秒
            # 例如现在是 12:00:00.05，我们只睡 0.95秒，而不是 1.0秒
            # 这样下一次循环就会精准地落在 12:00:01.00 附近
            now = time.time()
            sleep_time = 1.0 - (now % 1.0)
            
            # 加上一点点缓冲防止浮点误差导致连续两次落在同一秒内
            if sleep_time < 0.001: 
                sleep_time += 1.0
                
            time.sleep(sleep_time)

    except (KeyboardInterrupt, BrokenPipeError, IOError):
        sys.exit(0)

if __name__ == "__main__":
    main()