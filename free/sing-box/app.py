import requests
import json
import re
import os
import sys
import hashlib
import yaml  # 必须安装: pip install pyyaml
from typing import Any, Dict, List, Tuple, Union

from flask import Flask, request, jsonify, Response, abort

# ===== 可修改配置项 =====

# 只要包含这些关键词的节点才会保留
NODE_REGION_KEYWORDS = ["JP", "SG", "HK", "US", "TW", "美国", "香港", "新加坡", "日本", "台湾"]
# 包含这些关键词的节点会被剔除
NODE_EXCLUDE_KEYWORDS = ["到期", "官网", "剩余", "10", "重置", "流量"]

# 模板文件映射配置
TEMPLATE_MAP = {
    "default": "openwrt.json",
    "pc": "pc.json",
    "m": "m.json",
}

# 密码哈希和API地址文件
MITCE_PASSWORD_HASH = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
MITCE_API_FILE = "mitce"
BAJIE_API_FILE = "bajie"

# ===== 缓存配置 =====
CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

app = Flask(__name__)


def clash_to_singbox(proxy: Dict[str, Any]) -> Dict[str, Any]:
    """
    核心函数：将 Clash 节点格式转换为 Sing-box 出站格式
    """
    p_type = proxy.get("type", "").lower()
    node = {
        "tag": proxy.get("name", "unnamed"),
        "server": proxy.get("server"),
        "server_port": proxy.get("port"),
    }

    # === Shadowsocks ===
    if p_type == "ss":
        node["type"] = "shadowsocks"
        node["method"] = proxy.get("cipher")
        node["password"] = proxy.get("password")
        if "plugin" in proxy:
            plugin = proxy.get("plugin")
            plugin_opts = proxy.get("plugin-opts", {})
            if plugin == "obfs":
                node["plugin"] = "obfs-local"
                node["plugin_opts"] = {
                    "mode": plugin_opts.get("mode", "http"),
                    "host": plugin_opts.get("host", "")
                }

    # === VMess ===
    elif p_type == "vmess":
        node["type"] = "vmess"
        node["uuid"] = proxy.get("uuid")
        node["alter_id"] = proxy.get("alterId", 0)
        node["security"] = proxy.get("cipher", "auto")
        
        network = proxy.get("network", "tcp")
        transport = {}
        
        if network == "ws":
            transport["type"] = "ws"
            ws_opts = proxy.get("ws-opts", {})
            transport["path"] = ws_opts.get("path", "/")
            if "headers" in ws_opts and "Host" in ws_opts["headers"]:
                transport["headers"] = {"Host": ws_opts["headers"]["Host"]}
        elif network == "grpc":
            transport["type"] = "grpc"
            grpc_opts = proxy.get("grpc-opts", {})
            transport["service_name"] = grpc_opts.get("grpc-service-name", "")
            
        if transport:
            node["transport"] = transport

        if proxy.get("tls"):
            tls = {"enabled": True}
            if proxy.get("servername"):
                tls["server_name"] = proxy.get("servername")
            if proxy.get("skip-cert-verify"):
                tls["insecure"] = True
            node["tls"] = tls

    # === Trojan ===
    elif p_type == "trojan":
        node["type"] = "trojan"
        node["password"] = proxy.get("password")
        tls = {"enabled": True}
        if proxy.get("sni"):
            tls["server_name"] = proxy.get("sni")
        if proxy.get("skip-cert-verify"):
            tls["insecure"] = True
        node["tls"] = tls
        
        network = proxy.get("network", "tcp")
        if network == "ws":
             transport = {"type": "ws"}
             ws_opts = proxy.get("ws-opts", {})
             transport["path"] = ws_opts.get("path", "/")
             if "headers" in ws_opts and "Host" in ws_opts["headers"]:
                transport["headers"] = {"Host": ws_opts["headers"]["Host"]}
             node["transport"] = transport

    # === Hysteria2 ===
    elif p_type == "hysteria2":
        node["type"] = "hysteria2"
        node["password"] = proxy.get("password")
        if "obfs" in proxy:
            node["obfs"] = {
                "type": "salamander",
                "password": proxy.get("obfs-password", "")
            }
        tls = {
            "enabled": True,
            "insecure": proxy.get("skip-cert-verify", False)
        }
        if proxy.get("sni"):
            tls["server_name"] = proxy.get("sni")
        node["tls"] = tls

    else:
        return None

    return node


@app.route("/<source>", methods=["GET"])
def process_nodes_from_source(source: str) -> Union[Response, Tuple[Response, int]]:
    # 1. 自动检测配置模板
    ua = request.headers.get("User-Agent", "")
    if "SFA" in ua:
        detected_config = "m"
    elif "sing-box_openwrt" in ua:
        detected_config = "default"
    elif "sing-box" in ua:
        detected_config = "pc"
    else:
        detected_config = "default"

    # 2. 获取参数
    config_param = request.args.get("config", detected_config)

    # 3. 鉴权
    key = request.args.get("key", "")
    if not key:
        return jsonify({"error": "未授权访问"}), 403

    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if key_hash != MITCE_PASSWORD_HASH:
        return jsonify({"error": "未鉴权访问"}), 403

    # 选择源文件
    if source == "mitce":
        api_file = MITCE_API_FILE
    elif source == "bajie":
        api_file = BAJIE_API_FILE
    else:
        return jsonify({"error": "不支持的参数"}), 403

    cache_file_path = os.path.join(CACHE_DIR, f"{source}.yaml")
    yaml_content = ""

    # 4. 获取数据逻辑
    try:
        file_path = os.path.join(os.path.dirname(__file__), api_file)
        with open(file_path, "r", encoding="utf-8") as f:
            url = f.read().strip()
            if not url:
                raise ValueError(f"{source} 文件内容为空")

        # --- 网络请求 ---
        headers = {
            "User-Agent": "clash-verge",
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # === 核心修改：直接获取文本，不做任何解码尝试 ===
        yaml_content = response.text.strip()
        
        # 写入缓存
        with open(cache_file_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
            
        print(f"[{source}] 网络拉取成功", file=sys.stdout)

    except Exception as e:
        # --- 降级处理：读取缓存 ---
        print(f"[{source}] 网络失败 ({str(e)})，使用本地缓存...", file=sys.stderr)
        if os.path.exists(cache_file_path):
            with open(cache_file_path, "r", encoding="utf-8") as f:
                yaml_content = f.read()
        else:
            return jsonify({"error": f"获取失败且无本地缓存: {str(e)}"}), 500

    # 5. 解析 YAML 并转换为 Sing-box 格式
    try:
        try:
            clash_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as ye:
            return jsonify({"error": f"YAML 解析失败: {str(ye)}", "preview": yaml_content[:100]}), 400

        if not isinstance(clash_data, dict) or "proxies" not in clash_data:
            return jsonify({"error": "无效的 Clash 配置：未找到 proxies 字段"}), 400

        raw_proxies = clash_data["proxies"]
        nodes = []
        
        for proxy in raw_proxies:
            try:
                sb_node = clash_to_singbox(proxy)
                if sb_node:
                    nodes.append(sb_node)
            except Exception:
                continue

        if not nodes:
            return jsonify({"error": "没有转换成功的节点"}), 400

        # 6. 模板处理与合并
        template_filename = TEMPLATE_MAP.get(config_param, TEMPLATE_MAP["default"])
        config_path = os.path.join(os.path.dirname(__file__), template_filename)

        if not os.path.exists(config_path):
            return jsonify({"error": f"模板文件未找到: {template_filename}"}), 500

        with open(config_path, "r", encoding="utf-8") as f:
            base_config = json.load(f)

        outbounds = base_config.get("outbounds", [])
        existing_tags = {o.get("tag") for o in outbounds}
        
        new_nodes = [
            n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags
        ]
        outbounds.extend(new_nodes)

        # --- 过滤逻辑 ---
        def node_tag_valid(tag: str) -> bool:
            tag_upper = tag.upper() if tag else ""
            if not any(region.upper() in tag_upper for region in NODE_REGION_KEYWORDS):
                return False
            if any(exclude in tag for exclude in NODE_EXCLUDE_KEYWORDS):
                return False
            return True

        filtered_outbounds = [
            o for o in outbounds
            if node_tag_valid(o.get("tag", "")) 
            or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]
        ]

        # --- 处理 Selector/URLTest 的正则筛选 ---
        for outbound in filtered_outbounds:
            if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
                regex_list = [
                    reg for f in outbound.get("filter", [])
                    for reg in f.get("regex", [])
                ]
                
                del outbound["filter"]
                
                if not regex_list:
                    continue

                pattern = "|".join(regex_list)
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    all_valid_tags = [
                        o.get("tag") for o in filtered_outbounds
                        if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]
                    ]
                    matched_tags = [tag for tag in all_valid_tags if compiled.search(tag)]
                    
                    if matched_tags:
                        outbound["outbounds"] = matched_tags
                    else:
                        outbound["outbounds"] = ["DIRECT"] 
                except re.error as e:
                    print(f"无效的正则表达式 '{pattern}': {e}", file=sys.stderr)

        base_config["outbounds"] = filtered_outbounds

        json_str = json.dumps(base_config, ensure_ascii=False, indent=2)
        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=config.json"},
        )
        
    except Exception as e:
        return jsonify({"error": f"处理过程中发生错误: {str(e)}", "source": source}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)