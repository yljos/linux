from flask import Flask, jsonify
import requests
import os
import logging
from dotenv import load_dotenv
import datetime
import pytz
import threading

load_dotenv()

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------- 全局变量 ----------------
china_timezone = pytz.timezone("Asia/Shanghai")
LOG_FILE = "yao_online.txt"
file_lock = threading.Lock()

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")


# ---------------- 工具函数 ----------------
def send_telegram_message(message: str) -> dict:
    """发送 Telegram 消息，使用 HTML 格式"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        # 增加超时设置，防止卡死
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        app.logger.error(f"Telegram API Request failed: {e}")
        return {"ok": False, "description": str(e)}


def notify_and_respond(event: str, message: str, success_data: dict):
    """统一发送 Telegram 消息并返回 JSON 响应"""
    try:
        response = send_telegram_message(message)
        if response.get("ok"):
            app.logger.info(f"{event.capitalize()} notification sent successfully")
            return jsonify({"status": "success", **success_data})
        else:
            app.logger.error(f"Failed to send {event} notification: {response}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Notification send failed",
                        "details": response,
                    }
                ),
                500,
            )
    except Exception as e:
        app.logger.error(f"{event.capitalize()} notification exception: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Notification send exception",
                    "details": str(e),
                }
            ),
            500,
        )


# ---------------- 路由 ----------------
@app.route("/online")
def online():
    """记录上线事件并发送通知"""
    timestamp = datetime.datetime.now(china_timezone)

    # 【逻辑完善】增加锁的大范围覆盖，保证 读取->判断->写入 是原子操作
    with file_lock:
        # 1. 读取最后一行检查状态
        last_line = ""
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1]
        except Exception:
            pass

        # 2. 如果已经是 ONLINE，直接忽略
        if last_line.startswith("ONLINE|"):
            return jsonify(
                {"status": "ignored", "message": "Already ONLINE. Action skipped."}
            )

        # 3. 写入日志 (锁依然被持有，安全)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"ONLINE|{timestamp.isoformat()}\n")
        except IOError as e:
            app.logger.error(f"Error writing log: {e}")

    # 4. 发送通知 (放在锁外面，避免网络请求阻塞文件锁)
    message = (
        f"<b>大瑶 上线</b>\n" f"<b>时间</b>: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return notify_and_respond(
        "online",
        message,
        {
            "message": "Online notification sent",
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@app.route("/offline")
def offline():
    """记录下线事件并发送通知"""
    offline_timestamp = datetime.datetime.now(china_timezone)
    online_time_str = "未记录"
    uptime_str = "未知"

    # 【逻辑完善】大范围锁，确保 Check-Calculate-Write 是原子操作
    with file_lock:
        lines = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()

        # 1. 检查状态：如果文件为空或最后一行不是 ONLINE，则忽略
        if not lines or not lines[-1].startswith("ONLINE|"):
            return jsonify(
                {
                    "status": "ignored",
                    "message": "Current status is NOT online. Action skipped.",
                }
            )

        # 2. 直接从内存中获取上线时间
        try:
            _, ts_str = lines[-1].strip().split("|")
            online_timestamp = datetime.datetime.fromisoformat(ts_str)

            # 计算时长
            delta = offline_timestamp - online_timestamp
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, remainder = divmod(remainder, 60)
            seconds = int(remainder)
            uptime_str = f"{int(hours)}小时 {int(minutes)}分钟 {seconds}秒"
            online_time_str = online_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            app.logger.error("Log format error")

        # 3. 写入下线记录
        try:
            with open(LOG_FILE, "a") as f:
                f.write(f"OFFLINE|{offline_timestamp.isoformat()}\n")
        except IOError as e:
            app.logger.error(f"Error writing log: {e}")

    offline_time_str = offline_timestamp.strftime("%Y-%m-%d %H:%M:%S")

    message = (
        f"<b>大瑶 下线</b>\n"
        f"<b>上线时间</b>: {online_time_str}\n"
        f"<b>下线时间</b>: {offline_time_str}\n"
        f"<b>在线时长</b>: {uptime_str}"
    )

    return notify_and_respond(
        "offline",
        message,
        {
            "message": "Offline notification sent",
            "online_at": online_time_str,
            "offline_at": offline_time_str,
            "uptime": uptime_str,
        },
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5007, debug=False)
