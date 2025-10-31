#!/usr/bin/env python3
"""
Hysteria2 URL to YAML converter
转换为包含默认参数的Clash配置格式
"""

import json
from urllib.parse import urlparse, parse_qs
import urllib.parse


def parse_hysteria2_url(url):
    """
    解析Hysteria2 URL，返回配置字典
    包含必要的默认参数，与Clash配置格式保持一致
    """
    # 解析URL
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # 检查是否为hysteria2协议
    if not url.startswith("hysteria2://"):
        raise ValueError("不是有效的Hysteria2 URL")

    # 获取节点名称 (fragment部分)
    node_name = parsed.fragment if parsed.fragment else "Hysteria2节点"
    # URL解码节点名称
    node_name = urllib.parse.unquote(node_name)

    # 检查必要参数
    if not parsed.hostname or not parsed.port or not parsed.username:
        raise ValueError(
            f"URL缺少必要信息: server={parsed.hostname}, port={parsed.port}, password={parsed.username}"
        )

    # 根据端口号确定端口范围
    port = parsed.port
    if 1000 <= port <= 2000:
        ports_range = "1000-2000"
    elif 3000 <= port <= 4000:
        ports_range = "3000-4000"
    elif 5000 <= port <= 6000:
        ports_range = "5000-6000"
    elif 7000 <= port <= 8000:
        ports_range = "7000-8000"
    elif 9000 <= port <= 10000:
        ports_range = "9000-10000"
    elif 11000 <= port <= 12000:
        ports_range = "11000-12000"
    elif 13000 <= port <= 14000:
        ports_range = "13000-14000"
    elif 15000 <= port <= 16000:
        ports_range = "15000-16000"
    elif 17000 <= port <= 18000:
        ports_range = "17000-18000"
    elif 19000 <= port <= 20000:
        ports_range = "19000-20000"
    else:
        # 默认端口范围
        ports_range = None

    # 目标结构
    sni = query["sni"][0] if "sni" in query and query["sni"][0] else parsed.hostname
    up_speed = query.get("upmbps", query.get("up", ["20"]))[0]
    down_speed = query.get("downmbps", query.get("down", ["40"]))[0]
    # 端口范围格式调整
    config = {
        "type": "hysteria2",
        "tag": node_name,
        "server": parsed.hostname,
        "server_port": port,
        "up_mbps": int(up_speed),
        "down_mbps": int(down_speed),
        "password": parsed.username,
        "tls": {"enabled": True, "server_name": sni},
    }
    if ports_range:
        config["server_ports"] = ports_range.replace("-", ":")
    return config


def convert_url_to_json(url):
    """
    将Hysteria2 URL转换为JSON字符串
    """
    config = parse_hysteria2_url(url)
    return json.dumps(config, ensure_ascii=False, indent=2)


def main(url):
    """主函数 - 直接转换URL"""
    return parse_hysteria2_url(url)


if __name__ == "__main__":
    pass
