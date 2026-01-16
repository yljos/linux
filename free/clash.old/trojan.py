#!/usr/bin/env python3
"""
Trojan URL to YAML converter
转换为包含默认参数的Clash配置格式
"""

import yaml
from urllib.parse import urlparse, parse_qs
import urllib.parse
from typing import Any, Dict


def parse_trojan_url(url: str) -> Dict[str, Any]:
    """
    解析Trojan URL，返回配置字典
    包含必要的默认参数，与Clash配置格式保持一致
    """
    # 解析URL
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    # 检查是否为trojan协议
    if not url.startswith("trojan://"):
        raise ValueError("不是有效的Trojan URL")

    # 获取节点名称 (fragment部分)
    node_name = parsed.fragment if parsed.fragment else "Trojan节点"
    # URL解码节点名称
    node_name = urllib.parse.unquote(node_name)

    # 检查必要参数
    if not parsed.hostname or not parsed.port or not parsed.username:
        raise ValueError(
            f"URL缺少必要信息: server={parsed.hostname}, port={parsed.port}, password={parsed.username}"
        )

    # 基础配置 - 默认设置为 skip-cert-verify: True
    config: Dict[str, Any] = {
        "name": node_name,
        "type": "trojan",
        "server": parsed.hostname,
        "port": parsed.port,
        "password": parsed.username,
        "udp": True,  # 默认启用UDP
        "sni": "",  # 服务器名称，根据sni参数设置
        "skip-cert-verify": True,  # <-- 关键修改：默认设置为 True
    }

    # 处理SNI参数
    if "sni" in query and query["sni"][0]:
        config["sni"] = query["sni"][0]
    else:
        # 如果没有指定sni，使用服务器地址作为默认值
        config["sni"] = parsed.hostname

    # --- 关键修改：处理 insecure 参数 ---
    # 只有当 allowInsecure=false 时，才移除默认的 skip-cert-verify: true
    if "allowInsecure" in query:
        if query["allowInsecure"][0].lower() == "false":
            # 如果明确要求验证证书，则将默认值覆盖为 False
            config["skip-cert-verify"] = False
    # --- 关键修改结束 ---

    # 处理传输协议 (默认为 tcp)
    network_type = query.get("type", [""])[0]

    # 仅当 type 参数存在且不等于 "tcp" 时，才显式设置 network
    if network_type and network_type != "tcp":
        config["network"] = network_type

    # 处理 WebSocket 配置
    if network_type == "ws":
        ws_opts: Dict[str, Any] = {}

        # 路径
        if "path" in query and query["path"][0]:
            ws_opts["path"] = query["path"][0]

        # Host Header
        headers: Dict[str, Any] = {}
        if "host" in query and query["host"][0]:
            headers["Host"] = query["host"][0]

        if headers:
            ws_opts["headers"] = headers

        if ws_opts:
            config["ws-opts"] = ws_opts

    # 处理 gRPC 配置
    elif network_type == "grpc":
        grpc_opts: Dict[str, Any] = {}
        if "serviceName" in query and query["serviceName"][0]:
            grpc_opts["grpc-service-name"] = query["serviceName"][0]

        if grpc_opts:
            config["grpc-opts"] = grpc_opts

    # 清理空值和无效配置
    cleaned_config: Dict[str, Any] = {}
    for key, value in config.items():
        if value is not None and value != "" and value != {}:
            if isinstance(value, dict):
                # 对于字典类型，检查是否为空或包含空值
                cleaned_dict = {
                    k: v for k, v in value.items() if v is not None and v != ""
                }
                if cleaned_dict:
                    cleaned_config[key] = cleaned_dict
            else:
                cleaned_config[key] = value

    # 在最终清理步骤之后，如果 skip-cert-verify 为 False，则不包含它
    if cleaned_config.get("skip-cert-verify") is False:
        del cleaned_config["skip-cert-verify"]

    return cleaned_config


def convert_url_to_yaml(url: str) -> str:
    """
    将Trojan URL转换为YAML字符串
    """
    config = parse_trojan_url(url)
    clash_config = {"proxies": [config]}

    # 添加自定义布尔值表示器，确保输出为小写 "true" / "false"
    def boolean_representer(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:bool", str(data).lower())

    yaml.add_representer(bool, boolean_representer)

    return yaml.dump(
        clash_config,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        default_style=None,
        sort_keys=False,
        width=float("inf"),  # 防止长字符串被折行
    )


def main(url: str) -> Dict[str, Any]:
    """主函数 - 直接转换URL"""
    return parse_trojan_url(url)


if __name__ == "__main__":
    pass
