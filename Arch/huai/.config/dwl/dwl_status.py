#!/usr/bin/env python3
"""
DWL Status Bar Generator
功能完全等同于 dwl_status.sh
优化：使用多线程异步更新天气，解决启动和运行时卡顿问题
"""

import os
import sys
import time
import signal
import subprocess
import threading  # 新增：用于异步更新
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
INTERFACE = "enp0s31f6"  # 网卡名称
WEATHER_LOCATION = ""  # 留空自动检测，或指定如 "Beijing" 或 "~北京"
LOCATION_GPG = str(
    Path.home() / ".config" / "location.gpg"
)  # optional encrypted location


def _try_load_location_from_gpg(timeout: int = 5):
    """Try to decrypt LOCATION_GPG and return the location string or None.

    This is safe to call repeatedly; failures are silently ignored.
    """
    try:
        if not LOCATION_GPG or not os.path.isfile(LOCATION_GPG):
            return None
        # run gpg in non-interactive/batch mode and detach stdin to avoid pinentry
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
UPDATE_INTERVAL_MEDIUM = 5  # 中等频率更新间隔(秒)
UPDATE_INTERVAL_LONG = 60  # 长时间更新间隔(秒) - 时间
UPDATE_INTERVAL_WEATHER = 1800  # 天气更新间隔(秒) - 30分钟
SEPARATOR = "|"  # 各模块之间的分隔符

# =============================================================================
# --- GLOBAL STATE ---
# =============================================================================


class StatusBar:
    def __init__(self):
        # 如果未在配置中指定 WEATHER_LOCATION，尝试从 location.gpg 中读取
        global WEATHER_LOCATION
        if not WEATHER_LOCATION and LOCATION_GPG:
            try:
                # 使用 gpg 解密文件（以非交互模式运行以避免 pinentry 弹窗）
                res = subprocess.run(
                    ["gpg", "--batch", "--yes", "-d", LOCATION_GPG],
                    capture_output=True,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    timeout=5,
                )
                if res.returncode == 0 and res.stdout.strip():
                    loc = res.stdout.strip()
                    # 展开 ~ 并去除多余空白
                    loc = os.path.expanduser(loc)
                    WEATHER_LOCATION = loc
            except Exception:
                # 忽略解密错误，保持 WEATHER_LOCATION 为空
                pass

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
        self.weather_status = ""

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
        self.time_status = datetime.now().strftime("%Y-%m-%d %H:%M %a")

    def update_weather_async(self):
        """[新增] 异步更新天气，防止卡死"""
        thread = threading.Thread(target=self.update_weather)
        thread.daemon = True
        thread.start()

    def update_weather(self):
        """更新天气信息"""
        try:
            # ensure we can assign to the module WEATHER_LOCATION when needed
            global WEATHER_LOCATION
            # 使用 wttr.in 服务获取天气
            # 格式: %t 温度, %C 天气状况文字
            # If WEATHER_LOCATION is empty, attempt to load from encrypted file on each update.
            location = WEATHER_LOCATION or ""
            if not location:
                loc = _try_load_location_from_gpg()
                if loc:
                    # set module-level location so future updates reuse it
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

                # extract temperature substring (e.g. +12°C or 12°C)
                # match digits with optional sign and optional °C
                temp_match = re.search(r"([+-]?\d+\s*°?C?)", weather)
                temp_str = None
                if temp_match:
                    temp_str = temp_match.group(1).strip()

                # determine temperature color: <20 blue, 20-26 green, >26 yellow
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

                # determine condition substring (everything after temp) and its color
                cond_str = weather
                if temp_str:
                    # remove the first occurrence of temp_str from weather to get condition
                    cond_str = weather.replace(temp_str, "", 1).strip()

                # condition color: expanded English keyword lists
                # Keep existing color mapping but include more common terms
                cond_color = C_NORM
                # severe / dangerous weather
                if any(
                    k in lw
                    for k in (
                        "tornado",
                        "hurricane",
                        "typhoon",
                        "cyclone",
                        "squall",
                        "squalls",
                        "snow",
                        "blizzard",
                        "thunderstorm",
                        "storm",
                        "thunder",
                    )
                ):
                    cond_color = C_CRIT
                # precipitation / rain-like
                elif any(
                    k in lw
                    for k in (
                        "rain",
                        "rains",
                        "showers",
                        "shower",
                        "drizzle",
                        "sleet",
                        "hail",
                        "freezing",
                        "freezing rain",
                        "freezing-rain",
                        "ice",
                        "ice pellets",
                    )
                ):
                    cond_color = C_BLUE
                # low visibility / mist/fog/haze/smoke
                elif any(k in lw for k in ("mist", "fog", "haze", "smoke")):
                    cond_color = C_BLUE
                # dust / sand / ash events
                elif any(k in lw for k in ("dust", "sand", "ash")):
                    cond_color = C_BLUE
                # clouds / overcast (neutral)
                elif any(
                    k in lw
                    for k in (
                        "cloud",
                        "clouds",
                        "cloudy",
                        "overcast",
                        "broken",
                        "scattered",
                        "few",
                    )
                ):
                    cond_color = C_NORM
                # clear / sunny
                elif any(k in lw for k in ("sun", "clear", "sunny")):
                    cond_color = C_NORM

                # assemble: ICON + colored temp + colored condition
                if temp_str:
                    self.weather_status = f"{ICON_WEATHER}{temp_color}{temp_str}{C_RESET} {cond_color}{cond_str}{C_RESET}"
                else:
                    # fallback: color whole string by condition
                    self.weather_status = (
                        f"{ICON_WEATHER}{cond_color}{weather}{C_RESET}"
                    )
            else:
                self.weather_status = f"{ICON_WEATHER}N/A"
        except:
            self.weather_status = f"{ICON_WEATHER}N/A"

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

    # 信号处理函数
    def handle_volume_change(signum, frame):
        """处理音量改变信号 (SIGUSR1)"""
        status.update_volume()
        status.print_status_bar()

    def handle_ime_change(signum, frame):
        """处理输入法改变信号 (SIGUSR2)"""
        status.update_ime()
        status.print_status_bar()

    def handle_pipe_signal(signum, frame):
        """处理管道断开信号 (SIGPIPE)"""
        sys.exit(0)

    # 注册信号处理器
    # 使用 SIGUSR1 代替 SIGRTMIN+2 (音量改变)
    # 使用 SIGUSR2 代替 SIGRTMIN+3 (输入法改变)
    signal.signal(signal.SIGUSR1, handle_volume_change)
    signal.signal(signal.SIGUSR2, handle_ime_change)
    # 处理管道断开 (dwl 退出时)
    signal.signal(signal.SIGPIPE, handle_pipe_signal)

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

    # 【修改点】使用异步更新天气，防止启动卡顿
    status.update_weather_async()

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

            if sec % UPDATE_INTERVAL_WEATHER == 0:
                # 【修改点】循环中也使用异步更新
                status.update_weather_async()

            status.print_status_bar()
            time.sleep(1)
            sec += 1
    except (KeyboardInterrupt, BrokenPipeError, IOError):
        # 优雅退出：Ctrl+C 或管道断开 (dwl 退出)
        sys.exit(0)


if __name__ == "__main__":
    main()
