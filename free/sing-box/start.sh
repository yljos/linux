#!/bin/bash
# 可以在这里做一些准备工作
pip install -r requirements.txt --no-cache-dir

# 最后启动 Python 时，加上 exec
# 这样 Python 会替换当前 Shell 进程，直接接收 Systemd 的信号
exec python app.py
