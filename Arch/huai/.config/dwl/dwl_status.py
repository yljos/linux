#!/usr/bin/env python3
"""
DWL Status Bar Generator (Python Optimized)
1. 异步天气 (硬编码位置 Weihai)
2. Socket 直连 MPD (零进程开销)
3. 精准时间对齐 (秒针无漂移)
"""

import os
import sys
import time
import signal
import subprocess
import threading
import socket
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

# [修改点] 直接固定位置 (拼音)
WEATHER_LOCATION = "Weihai"

# MPD 设置
MPD_HOST = "127.0.0.1"
MPD_PORT = 6600

# --- 4. Behavior Settings ---
UPDATE_INTERVAL_MEDIUM = 5
UPDATE_INTERVAL_LONG = 60
UPDATE_INTERVAL_WEATHER = 1800  # 30分钟
SEPARATOR = "|"

# =============================================================================
# --- GLOBAL STATE ---
# =============================================================================


class StatusBar:
    def __init__(self):
        # 初始化内核版本
        self.kernel_version = self._get_kernel_version()
        self.arch = f"{C_NORM}{self.kernel_version.split('-')[0]}{C_RESET}"

        # 初始化网络统计
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

        # 初始化 CPU 统计
        self.prev_cpu = 0
        self.prev_idle = 0
        self._update_cpu_baseline()

        # 状态变量
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
                # user+nice+system+idle+iowait+irq+softirq
                cpu_vals = [int(x) for x in line[1:8]]
                self.prev_cpu = sum(cpu_vals)
                self.prev_idle = cpu_vals[3]  # idle is index 3 (4th value)
        except:
            pass

    def update_cpu(self):
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline().split()
                cpu_vals = [int(x) for x in line[1:8]]
                curr_cpu = sum(cpu_vals)
                curr_idle = cpu_vals[3]

                total_diff = curr_cpu - self.prev_cpu
                idle_diff = curr_idle - self.prev_idle

                usage = 0
                if total_diff > 0:
                    usage = int(100 * (total_diff - idle_diff) / total_diff)

                self.prev_cpu = curr_cpu
                self.prev_idle = curr_idle

                if usage >= 90:
                    color = C_CRIT
                elif usage >= 75:
                    color = C_WARN
                else:
                    color = C_NORM

                self.cpu_status = f"{color}{usage:02d}%{C_RESET}"
        except:
            self.cpu_status = "N/A"

    def update_mem(self):
        try:
            with open("/proc/meminfo", "r") as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    meminfo[parts[0].rstrip(":")] = int(parts[1])

                total_mb = meminfo.get("MemTotal", 0) // 1024
                available_mb = meminfo.get("MemAvailable", 0) // 1024
                used_mb = total_mb - available_mb

                self.mem_status = f"{used_mb}/{total_mb}MB"
        except:
            self.mem_status = "N/A"

    def update_temp(self):
        try:
            if self._file_readable(CPU_TEMP_FILE):
                with open(CPU_TEMP_FILE, "r") as f:
                    temp_val = int(int(f.read().strip()) / 1000)

                if temp_val >= 80:
                    color = C_CRIT
                elif temp_val >= 65:
                    color = C_WARN
                else:
                    color = C_NORM

                self.temp_status = f"{ICON_TEMP}{color}{temp_val}°C{C_RESET}"
            else:
                self.temp_status = f"{ICON_TEMP}N/A"
        except:
            self.temp_status = f"{ICON_TEMP}N/A"

    def update_bluetooth(self):
        self.bluetooth_status = ""
        # 快速检查进程，避免无效调用
        try:
            subprocess.run(
                ["pgrep", "-x", "bluetoothd"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except subprocess.CalledProcessError:
            return

        try:
            result = subprocess.run(
                ["bluetoothctl", "info"], capture_output=True, text=True, timeout=2
            )
            # 使用正则直接提取电量，比遍历行更快
            match = re.search(r"Battery Percentage: \((\d+)\)", result.stdout)
            if match:
                level = int(match.group(1))
                if level <= 20:
                    color = C_CRIT
                elif level <= 30:
                    color = C_WARN
                else:
                    color = C_NORM
                self.bluetooth_status = f"{ICON_BT}{color}{level}%{C_RESET}"
        except:
            pass

    def update_volume(self):
        try:
            # 简化命令调用
            result = subprocess.run(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                capture_output=True,
                text=True,
            )
            match = re.search(r"(\d+)%", result.stdout)
            vol = int(match.group(1)) if match else 50
            self.vol_status = f"{vol:02d}%"
        except:
            self.vol_status = "50%"

    def update_music(self):
        """Socket 连接 MPD，极速无进程"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                s.connect((MPD_HOST, MPD_PORT))
                s.send(b"currentsong\nstatus\nclose\n")

                data = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    data += chunk

                response = data.decode("utf-8", errors="ignore")

                state = "stop"
                artist = ""
                title = ""
                name = ""

                for line in response.splitlines():
                    if line.startswith("state: "):
                        state = line[7:]
                    elif line.startswith("Artist: "):
                        artist = line[8:]
                    elif line.startswith("Title: "):
                        title = line[7:]
                    elif line.startswith("Name: "):
                        name = line[6:]

                if state == "play":
                    display = (
                        f"{artist} - {title}"
                        if artist and title
                        else (title or name or "Unknown")
                    )
                    self.music_status = f"{C_NORM}{display}{C_RESET}"
                else:
                    self.music_status = ""
        except:
            self.music_status = ""

    def update_ime(self):
        try:
            result = subprocess.run(
                ["fcitx5-remote"], capture_output=True, text=True, timeout=1
            )
            if result.stdout.strip() == "2":
                self.ime_status = f"{C_WARN}CN{C_RESET}"
            else:
                self.ime_status = f"{C_NORM}EN{C_RESET}"
        except:
            self.ime_status = f"{C_NORM}EN{C_RESET}"

    def update_time(self):
        self.time_status = datetime.now().strftime("%Y-%m-%d %H:%M %a")

    def update_weather_async(self):
        # 开启独立线程更新，完全不阻塞
        threading.Thread(target=self._fetch_weather, daemon=True).start()

    def _fetch_weather(self):
        try:
            url = f"wttr.in/{WEATHER_LOCATION}?format=%t+%C"
            result = subprocess.run(
                ["curl", "-s", "-m", "10", url], capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                weather = result.stdout.strip()

                # 提取温度数字用于颜色判断
                temp_match = re.search(r"([+-]?\d+)", weather)
                temp_val = int(temp_match.group(1)) if temp_match else 20

                if temp_val <= 10:
                    temp_color = C_BLUE
                elif temp_val >= 32:
                    temp_color = C_CRIT
                elif temp_val >= 26:
                    temp_color = C_WARN
                else:
                    temp_color = C_NORM

                # 分离温度文本和天气状况
                # 假设格式如 "+25°C Sunny"
                full_temp_match = re.search(r"([+-]?\d+\s*°?C?)", weather)
                temp_str = full_temp_match.group(1) if full_temp_match else ""
                cond_str = weather.replace(temp_str, "").strip()

                if temp_str:
                    self.weather_status = (
                        f"{ICON_WEATHER}{temp_color}{temp_str}{C_RESET} {cond_str}"
                    )
                else:
                    self.weather_status = f"{ICON_WEATHER}{weather}"
            else:
                pass  # 保持上一次的状态，不更新为 N/A，避免闪烁
        except:
            pass

    def update_net(self):
        if self.rx1 is None:
            return
        try:
            with open(self.net_rx_file) as f:
                rx2 = int(f.read())
            with open(self.net_tx_file) as f:
                tx2 = int(f.read())

            rx_mbps = ((rx2 - self.rx1) * 8) // 1000000
            tx_mbps = ((tx2 - self.tx1) * 8) // 1000000

            self.rx1 = rx2
            self.tx1 = tx2
            self.net_status_str = (
                f"{ICON_NET_DOWN}{rx_mbps}Mbps {ICON_NET_UP}{tx_mbps}Mbps"
            )
        except:
            self.net_status_str = "N/A"

    def print_status_bar(self):
        parts = [
            f"{ICON_ARCH}{self.arch}",
            self.music_status,
            self.temp_status,
            f"{ICON_CPU}{self.cpu_status}",
            f"{ICON_MEM}{self.mem_status}",
            self.bluetooth_status,
            f"{ICON_VOL}{self.vol_status}",
            self.net_status_str,
            self.weather_status,
            self.time_status,
            self.ime_status,
        ]
        # 过滤掉空字符串并用分隔符连接
        print(SEPARATOR.join(filter(None, parts)))
        sys.stdout.flush()


# =============================================================================
# --- MAIN ---
# =============================================================================


def main():
    status = StatusBar()

    # 信号处理
    signal.signal(
        signal.SIGUSR1, lambda s, f: (status.update_volume(), status.print_status_bar())
    )
    signal.signal(
        signal.SIGUSR2, lambda s, f: (status.update_ime(), status.print_status_bar())
    )
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # 处理管道关闭

    # 首次全量更新
    status.update_cpu()
    status.update_mem()
    status.update_temp()
    status.update_music()
    status.update_ime()
    status.update_time()
    status.update_net()
    status.update_volume()
    status.update_bluetooth()
    status.update_weather_async()

    try:
        while True:
            start_time = time.time()
            sec = int(start_time)

            # 1. 高频 (每秒)
            status.update_cpu()
            status.update_temp()
            status.update_net()
            status.update_time()

            # 2. 中频 (5秒)
            if sec % UPDATE_INTERVAL_MEDIUM == 0:
                status.update_mem()
                status.update_music()
                status.update_bluetooth()

            # 3. 低频 (30分钟)
            if sec % UPDATE_INTERVAL_WEATHER == 0:
                status.update_weather_async()

            status.print_status_bar()

            # 精准对齐下一秒，防止时间漂移
            sleep_time = 1.0 - (time.time() % 1.0)
            if sleep_time < 0.001:
                sleep_time += 1.0
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
