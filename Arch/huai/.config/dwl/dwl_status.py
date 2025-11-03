#!/usr/bin/env python3
"""
DWL Status Bar Generator
功能完全等同于 dwl_status.sh
"""

import os
import sys
import time
import signal
import subprocess
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

# --- 2. Colors ---
C_NORM = "^fg(00ff00)"
C_WARN = "^fg(ffff00)"
C_CRIT = "^fg(ff0000)"
C_RESET = "^fg()"

# --- 3. System Settings ---
CPU_TEMP_FILE = "/sys/class/thermal/thermal_zone0/temp"
INTERFACE = "enp0s31f6"  # 网卡名称

# --- 4. Behavior Settings ---
UPDATE_INTERVAL_MEDIUM = 5  # 中等频率更新间隔(秒)
UPDATE_INTERVAL_LONG = 60  # 长时间更新间隔(秒)
SEPARATOR = "|"  # 各模块之间的分隔符

# =============================================================================
# --- GLOBAL STATE ---
# =============================================================================


class StatusBar:
    def __init__(self):
        self.kernel_version = self._get_kernel_version()
        self.arch = f"{C_NORM}{self.kernel_version.split('-')[0]}{C_RESET}"

        # 初始化网络相关
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

        # 初始化CPU相关
        self.prev_cpu = 0
        self.prev_idle = 0
        self._update_cpu_baseline()

        # 初始化状态变量
        self.cpu_status = ""
        self.mem_status = ""
        self.temp_status = ""
        self.vol_status = ""
        self.music_status = ""
        self.ime_status = ""
        self.time_status = ""
        self.bluetooth_status = ""

    def _get_kernel_version(self):
        """获取内核版本"""
        try:
            return os.uname().release
        except:
            return "Unknown"

    def _file_readable(self, path):
        """检查文件是否可读"""
        try:
            return os.access(path, os.R_OK)
        except:
            return False

    def _update_cpu_baseline(self):
        """初始化CPU基线"""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline().split()
                cpu_user, cpu_nice, cpu_system, cpu_idle = (
                    int(line[1]),
                    int(line[2]),
                    int(line[3]),
                    int(line[4]),
                )
                cpu_iowait, cpu_irq, cpu_softirq = (
                    int(line[5]),
                    int(line[6]),
                    int(line[7]),
                )
                self.prev_cpu = (
                    cpu_user
                    + cpu_nice
                    + cpu_system
                    + cpu_idle
                    + cpu_iowait
                    + cpu_irq
                    + cpu_softirq
                )
                self.prev_idle = cpu_idle
        except:
            pass

    def update_cpu(self):
        """更新CPU使用率"""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline().split()
                cpu_user, cpu_nice, cpu_system, cpu_idle = (
                    int(line[1]),
                    int(line[2]),
                    int(line[3]),
                    int(line[4]),
                )
                cpu_iowait, cpu_irq, cpu_softirq = (
                    int(line[5]),
                    int(line[6]),
                    int(line[7]),
                )

                curr_cpu = (
                    cpu_user
                    + cpu_nice
                    + cpu_system
                    + cpu_idle
                    + cpu_iowait
                    + cpu_irq
                    + cpu_softirq
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
        """更新内存使用情况"""
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
        """更新CPU温度"""
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
        """更新蓝牙信息"""
        self.bluetooth_status = ""

        # 检查bluetoothd是否运行
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

            # 提取电池电量
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

                        self.bluetooth_status = (
                            f"{ICON_BT}{color_code}{level}%{C_RESET}"
                        )
                        break
        except:
            pass

    def update_volume(self):
        """更新音量"""
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
        """更新音乐状态"""
        try:
            result = subprocess.run(["mpc"], capture_output=True, text=True, timeout=2)

            if "[playing]" in result.stdout:
                lines = result.stdout.split("\n")
                if lines:
                    music_line = lines[0]
                    # 提取 " - " 后面的部分
                    if " - " in music_line:
                        music = music_line.split(" - ")[-1]
                    else:
                        music = music_line

                    self.music_status = f"{C_NORM}{music or 'Off'}{C_RESET}"
            else:
                self.music_status = ""
        except:
            self.music_status = ""

    def update_ime(self):
        """更新输入法状态"""
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
        """更新时间"""
        self.time_status = datetime.now().strftime("%Y-%m-%d %H:%M %a" )

    def update_net(self):
        """更新网络速度"""
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

            self.net_status_str = (
                f"{ICON_NET_DOWN}{rx_mbps}Mbps {ICON_NET_UP}{tx_mbps}Mbps"
            )
        except:
            self.net_status_str = "N/A"

    def print_status_bar(self):
        """打印状态栏"""
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
        parts.append(self.time_status)
        parts.append(self.ime_status)

        print(f" {SEPARATOR} ".join(parts))
        sys.stdout.flush()


# =============================================================================
# --- MAIN EXECUTION ---
# =============================================================================


def main():
    status = StatusBar()

    # 信号处理
    def signal_handler(signum, frame):
        if signum == signal.SIGRTMIN + 2:  # 音量改变
            status.update_volume()
            status.print_status_bar()
        elif signum == signal.SIGRTMIN + 3:  # 输入法改变
            status.update_ime()
            status.print_status_bar()

    # 只能处理标准信号
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)

    # 首次运行
    status.update_cpu()
    status.update_mem()
    status.update_temp()
    status.update_music()
    status.update_ime()
    status.update_time()
    status.update_net()
    status.update_volume()
    status.update_bluetooth()

    # 主循环
    sec = 0
    try:
        while True:
            status.update_cpu()
            status.update_temp()
            status.update_net()

            if sec % UPDATE_INTERVAL_MEDIUM == 0:
                status.update_mem()
                status.update_music()
                status.update_bluetooth()

            if sec % UPDATE_INTERVAL_LONG == 0:
                status.update_time()

            status.print_status_bar()
            time.sleep(1)
            sec += 1
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
