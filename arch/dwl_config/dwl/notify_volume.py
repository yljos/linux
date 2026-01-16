#!/usr/bin/env python3
"""
通知 dwl_status.py 更新音量显示
使用方法: python3 notify_volume.py
"""

import os
import signal
import subprocess
import sys


def find_dwl_status_pid():
    """查找 dwl_status.py 进程的 PID"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "dwl_status.py"],
            capture_output=True,
            text=True,
            check=True,
        )
        pids = result.stdout.strip().split("\n")
        # 过滤掉当前脚本自己的 PID
        current_pid = os.getpid()
        pids = [int(pid) for pid in pids if pid and int(pid) != current_pid]
        return pids
    except subprocess.CalledProcessError:
        return []


def send_volume_signal():
    """发送音量更新信号 (SIGUSR1)"""
    pids = find_dwl_status_pid()

    if not pids:
        print("未找到运行中的 dwl_status.py 进程", file=sys.stderr)
        return False

    success = False
    for pid in pids:
        try:
            os.kill(pid, signal.SIGUSR1)
            print(f"成功发送 SIGUSR1 信号到进程 {pid}")
            success = True
        except ProcessLookupError:
            print(f"进程 {pid} 不存在", file=sys.stderr)
        except PermissionError:
            print(f"没有权限向进程 {pid} 发送信号", file=sys.stderr)

    return success


if __name__ == "__main__":
    if send_volume_signal():
        sys.exit(0)
    else:
        sys.exit(1)
