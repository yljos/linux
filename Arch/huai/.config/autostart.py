#!/usr/bin/env python3
"""
Autostart Python replacement (Asyncio + Pathlib Optimized)
- 并发启动：使用 asyncio 并行处理所有任务，不再顺序阻塞。
- 路径管理：完全使用 pathlib。
- 健壮性：增加 shutil.which 检查命令是否存在。
"""

import asyncio
import subprocess
import shutil
from pathlib import Path

# ================= 配置区域 =================
HOME = Path.home()
CONFIG_DIR = HOME / ".config"

# 定义脚本路径
SWWW_AUTO = CONFIG_DIR / "swww_auto.sh"
SHUTDOWN_SH = CONFIG_DIR / "shutdown.sh"

# ================= 工具函数 =================

async def is_running(pattern: str, exact: bool = True) -> bool:
    """
    异步检查进程是否运行。
    exact=True 使用 pgrep -x (精确匹配名称)
    exact=False 使用 pgrep -f (匹配完整命令行)
    """
    args = ["pgrep"]
    if exact:
        args.append("-x")
    else:
        args.append("-f")
    args.append(pattern)

    # 创建子进程运行 pgrep
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    await proc.wait()
    return proc.returncode == 0

async def notify(title: str, message: str, delay: int = 0):
    """异步发送通知"""
    if delay > 0:
        await asyncio.sleep(delay)
    
    # 检查 notify-send 是否存在
    if shutil.which("notify-send"):
        await asyncio.create_subprocess_exec(
            "notify-send", title, message,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

async def ensure_service(
    name: str, 
    cmd: list[str], 
    cwd: Path | None = None,
    match_pattern: str | None = None,
    check_delay: float = 3.0,
    notify_delay: int = 0,
    notify_msg: str = ""
):
    """
    核心逻辑：
    1. 检查是否已运行。
    2. 未运行 -> 启动 -> 等待 check_delay -> 再次检查。
    3. 再次检查失败 -> 发送通知。
    """
    # 确定用于匹配进程的模式（如果没指定，默认用 cmd[0] 的文件名）
    pattern = match_pattern if match_pattern else cmd[0]
    # 如果指定了 match_pattern，通常意味着我们需要 -f 模糊匹配
    exact_match = match_pattern is None

    # 1. 初始检查
    if await is_running(pattern, exact=exact_match):
        return # 已在运行，直接退出

    # 2. 预检：命令是否存在 (对于脚本，检查文件是否存在)
    executable = cmd[0]
    if executable.startswith("/") or executable.startswith("./"):
        # 如果是路径（如脚本），检查文件是否存在
        if not Path(executable).exists():
            await notify("Autostart Error", f"File not found: {executable}")
            return
    else:
        # 如果是命令（如 firefox），检查是否在 PATH 中
        if shutil.which(executable) is None:
            await notify("Autostart Error", f"Command not found: {executable}")
            return

    # 3. 启动进程 (使用 Popen 类似机制，不等待其结束)
    try:
        subprocess.Popen(
            cmd, 
            cwd=cwd,
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )
    except Exception as e:
        await notify("Autostart Exception", f"Failed to start {name}: {e}")
        return

    # 4. 异步等待（不阻塞其他任务）
    await asyncio.sleep(check_delay)

    # 5. 二次检查
    if not await is_running(pattern, exact=exact_match):
        if notify_msg:
            # 这里的 notify_delay 可以是相对于启动后的延迟
            # 但既然已经过了 check_delay，通常直接通知即可
            # 如果为了保持原脚本逻辑，我们这里再异步延时
            asyncio.create_task(
                notify("Autostart Failed", f"{notify_msg} failed to start", delay=max(0, notify_delay - int(check_delay)))
            )

# ================= 主入口 =================

async def main():
    # 使用 asyncio.gather 并发执行所有任务
    # 这意味着脚本只需等待所有任务中最慢的那一个（约3秒），而不是所有时间的总和。
    
    tasks = [
        # 1. Dunst
        ensure_service(
            "dunst", ["dunst"], notify_msg="dunst"
        ),
        
        # 2. SWWW Daemon
        ensure_service(
            "swww-daemon", ["swww-daemon"], 
            check_delay=3.0, notify_delay=2, notify_msg="swww-daemon"
        ),
        
        # 3. swww_auto.sh (Shell 脚本)
        ensure_service(
            "swww_auto.sh", 
            ["/bin/sh", str(SWWW_AUTO)], 
            match_pattern=str(SWWW_AUTO), # 使用完整路径匹配 (-f)
            check_delay=3.0, notify_delay=4, notify_msg="swww_auto.sh"
        ),
        
        # 4. shutdown.sh (Shell 脚本)
        ensure_service(
            "shutdown.sh", 
            ["/bin/sh", str(SHUTDOWN_SH)], 
            match_pattern=str(SHUTDOWN_SH), # 使用完整路径匹配 (-f)
            check_delay=3.0, notify_delay=6, notify_msg="shutdown.sh"
        ),
        
        # 5. Firefox
        ensure_service(
            "firefox", ["firefox"], 
            check_delay=3.0, notify_delay=8, notify_msg="Firefox"
        ),
        
        # 6. Telegram
        ensure_service(
            "Telegram", ["Telegram"], 
            check_delay=3.0, notify_delay=10, notify_msg="Telegram"
        ),
        
        # 7. Fcitx5
        ensure_service(
            "fcitx5", ["fcitx5", "-d"], 
            check_delay=3.0, notify_delay=12, notify_msg="fcitx5"
        ),
    ]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass