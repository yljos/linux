from flask import Flask, send_from_directory
import os
import threading
from datetime import datetime  # 添加datetime模块


app = Flask(__name__)

# 提取常量变量
SHUTDOWN_FILENAME = "/data/www/shutdown"
AUTO_DELETE_DELAY_MINUTES = 10  # 自动删除的延迟时间（分钟）


# 用于延迟删除文件的函数
def delayed_delete(filename, delay_minutes):
    """在指定分钟后删除文件"""
    threading.Timer(
        delay_minutes * 60,
        lambda: os.remove(filename) if os.path.exists(filename) else None,
    ).start()


@app.route("/favicon.ico")
def favicon():
    """提供网页图标"""
    return send_from_directory(
        os.path.dirname(os.path.abspath(__file__)), "favicon.png", mimetype="image/png"
    )


@app.route("/s")
def create_shutdown_file():
    """在根目录创建一个shutdown文件"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间
    try:
        with open(SHUTDOWN_FILENAME, "w") as f:
            f.write("1")  # 写入内容"1"
        return f"[{current_time}] 成功在根目录创建{SHUTDOWN_FILENAME}文件"
    except Exception as e:
        return f"[{current_time}] 创建{SHUTDOWN_FILENAME}文件失败: {str(e)}", 500


@app.route("/n")
def delete_shutdown_file():
    """从根目录删除shutdown文件"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间
    try:
        if os.path.exists(SHUTDOWN_FILENAME):
            os.remove(SHUTDOWN_FILENAME)
            return f"[{current_time}] 成功删除{SHUTDOWN_FILENAME}文件"
        else:
            return f"[{current_time}] {SHUTDOWN_FILENAME}文件不存在", 404
    except Exception as e:
        return f"[{current_time}] 删除{SHUTDOWN_FILENAME}文件失败: {str(e)}", 500


@app.route("/auto")
def auto_create_and_delete():
    """创建shutdown文件并在指定分钟后自动删除"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # 创建文件
        with open(SHUTDOWN_FILENAME, "w") as f:
            f.write("1")  # 写入内容"1"

        # 设置自动删除
        delayed_delete(SHUTDOWN_FILENAME, AUTO_DELETE_DELAY_MINUTES)

        return f"[{current_time}] 成功创建{SHUTDOWN_FILENAME}文件，将在{AUTO_DELETE_DELAY_MINUTES}分钟后自动删除"
    except Exception as e:
        return f"[{current_time}] 操作失败: {str(e)}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5008, debug=True)
