#!/usr/bin/env python3
"""
切换 fcitx5 输入法并通知 dwl_status.py 更新显示
使用方法: python3 notify_ime.py
"""

import os
import signal
import subprocess
import sys


def toggle_fcitx5():
    """切换 fcitx5 输入法"""
    try:
        subprocess.run(["fcitx5-remote", "-t"], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("切换输入法失败", file=sys.stderr)
        return False


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


def send_ime_signal():
    """发送输入法更新信号 (SIGUSR2)"""
    pids = find_dwl_status_pid()

    if not pids:
        print("未找到运行中的 dwl_status.py 进程", file=sys.stderr)
        return False

    success = False
    for pid in pids:
        try:
            os.kill(pid, signal.SIGUSR2)
            print(f"成功发送 SIGUSR2 信号到进程 {pid}")
            success = True
        except ProcessLookupError:
            print(f"进程 {pid} 不存在", file=sys.stderr)
        except PermissionError:
            print(f"没有权限向进程 {pid} 发送信号", file=sys.stderr)

    return success


if __name__ == "__main__":
    # 先切换输入法
    if not toggle_fcitx5():
        sys.exit(1)

    # 再发送信号通知状态栏更新
    if send_ime_signal():
        sys.exit(0)
    else:
        # 即使通知失败，输入法已经切换成功了
        sys.exit(0)
