import requests
import json
import re
import os
import sys
import hashlib
import yaml
from typing import Any, Dict, List, Tuple, Union
from flask import Flask, request, jsonify, Response, abort

app = Flask(__name__)

# ================= 配置区域 =================

# 1. 区域关键词 (保留这些地区)
NODE_REGION_KEYWORDS = ["JP", "SG", "HK", "US", "美国", "香港", "新加坡", "日本"]

# 2. 排除关键词 (黑名单)
NODE_EXCLUDE_KEYWORDS = [
    "到期",
    "官网",
    "剩余",
    "重置",
    "流量",
    "倍率",
    "HK3-HY2",
    "HK4-HY2",
    "HK5-HY2",
]

# 3. 节点重命名映射表 (中文 -> 英文)
RENAME_MAP = {
    "香港": "HK",
    "美国": "US",
    "新加坡": "SG",
    "日本": "JP",
    "家宽": "Home",
}

TEMPLATE_MAP = {
    "default": "openwrt.json",
    "pc": "pc.json",
    "m": "m.json",
}

MITCE_PASSWORD_HASH = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
MITCE_API_FILE = "mitce"
BAJIE_API_FILE = "bajie"

CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


# ================= 辅助函数 =================


def clean_node_name(name: str) -> str:
    """清洗节点名称：替换国家名 -> 移除图标/特殊字符 -> 去空格"""
    if not name:
        return name

    # 1. 关键词替换 (中文 -> 英文)
    for k, v in RENAME_MAP.items():
        name = name.replace(k, v)

    # 2. 移除所有非 ASCII 字符 (暴力去除图标、旗帜、剩余中文)
    # [^\x00-\x7F] 匹配所有非英文字符
    name = re.sub(r"[^\x00-\x7F]+", "", name)

    # 3. 清理多余空格 (例如 "US   Node" -> "US Node")
    name = re.sub(r"\s+", " ", name).strip()

    return name


# ================= 核心转换逻辑 =================


def process_shadowsocks(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "shadowsocks"
    # 直接读取 port
    node["server_port"] = int(proxy["port"])
    node["method"] = proxy.get("cipher")
    node["password"] = proxy.get("password")

    if "plugin" in proxy:
        plugin = proxy.get("plugin")
        plugin_opts = proxy.get("plugin-opts", {})

        # 针对 obfs 的特殊处理：必须拼接成字符串
        if plugin == "obfs":
            node["plugin"] = "obfs-local"
            mode = plugin_opts.get("mode", "http")
            host = plugin_opts.get("host", "")
            # 修正为字符串格式 "obfs=http;obfs-host=xxx"
            node["plugin_opts"] = f"obfs={mode};obfs-host={host}"

    return node


def process_vless(proxy: Dict[str, Any], base_node: Dict[str, Any]) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "vless"
    # 1. 端口 (直接读取)
    node["server_port"] = int(proxy["port"])
    node["uuid"] = proxy.get("uuid")
    node["flow"] = proxy.get("flow", "")
    # === 新增：处理 packet_encoding (如 xudp) ===
    if "packet-encoding" in proxy:
        node["packet_encoding"] = proxy["packet-encoding"]
    # ==========================================
    # 3. 传输层配置
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
    # 4. TLS 配置
    if proxy.get("tls") or proxy.get("reality-opts"):
        tls = {
            "enabled": True,
            "insecure": proxy.get("skip-cert-verify", False),
            "server_name": proxy.get("servername", ""),
        }
        if "reality-opts" in proxy:
            reality_opts = proxy.get("reality-opts", {})
            tls["reality"] = {
                "enabled": True,
                "public_key": reality_opts.get("public-key"),
                "short_id": reality_opts.get("short-id"),
            }
            if not tls["server_name"]:
                tls["server_name"] = proxy.get("sni", "")
        # === 修改：指纹处理 ===
        fingerprint = "firefox"
        tls["utls"] = {"enabled": True, "fingerprint": fingerprint}
        node["tls"] = tls
    return node


def process_hysteria2(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "hysteria2"
    node["password"] = proxy.get("password")
    # [修复] 优先读取 ports，如果没有则尝试读取单端口 port
    if "ports" in proxy:
        node["server_ports"] = proxy["ports"]
    elif "port" in proxy:
        node["server_port"] = int(proxy["port"])
    # 宽带速度处理 (默认: 上传 40 / 下载 100)
    node["up_mbps"] = 40
    node["down_mbps"] = 100
    if "obfs" in proxy:
        node["obfs"] = {
            "type": "salamander",
            "password": proxy.get("obfs-password", ""),
        }
    tls = {
        "enabled": True,
        "insecure": proxy.get("skip-cert-verify", False),
        "server_name": proxy.get("sni", ""),
    }
    node["tls"] = tls
    return node


def clash_to_singbox(proxy: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    p_type = proxy.get("type", "").lower()
    # base_node 只有 tag 和 server
    base_node = {"tag": proxy.get("name"), "server": proxy.get("server")}
    if p_type == "ss":
        return process_shadowsocks(proxy, base_node)
    elif p_type == "vless":
        return process_vless(proxy, base_node)
    elif p_type == "hysteria2":
        return process_hysteria2(proxy, base_node)
    else:
        return None


# ================= 路由处理逻辑 =================


@app.route("/<source>", methods=["GET"])
def process_nodes_from_source(source: str) -> Union[Response, Tuple[Response, int]]:
    ua = request.headers.get("User-Agent", "")
    if "SFA" in ua:
        detected_config = "m"
    elif "sing-box_openwrt" in ua:
        detected_config = "default"
    elif "sing-box_m" in ua:
        detected_config = "default"
    elif "sing-box_pc" in ua:
        detected_config = "pc"
    else:
        abort(404)
    config_param = request.args.get("config", detected_config)
    key = request.args.get("key", "")
    if not key:
        abort(404)
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if key_hash != MITCE_PASSWORD_HASH:
        abort(404)
    if source == "mitce":
        api_file = MITCE_API_FILE
    elif source == "bajie":
        api_file = BAJIE_API_FILE
    else:
        abort(404)
    cache_file_path = os.path.join(CACHE_DIR, f"{source}.yaml")
    yaml_content = ""
    # 3. 网络请求
    try:
        file_path = os.path.join(os.path.dirname(__file__), api_file)
        with open(file_path, "r", encoding="utf-8") as f:
            url = f.read().strip()
            if not url:
                raise ValueError(f"{source} 内容为空")
        # 严格只使用指定的 UA
        headers = {"User-Agent": "clash-verge"}
        print(f"[{source}] 正在拉取: {url[:25]}...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        temp_content = response.text.strip()
        # === 核心校验 ===
        # 拉取完立即检查是否有 proxies:
        if "proxies:" not in temp_content:
            raise ValueError("拉取校验失败")
        print(f"[{source}] 拉取通过")
        yaml_content = temp_content
        # 校验通过后再写入缓存
        with open(cache_file_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
    except Exception as e:
        print(f"[{source}] 网络/校验错误，使用缓存", file=sys.stderr)
        if os.path.exists(cache_file_path):
            with open(cache_file_path, "r", encoding="utf-8") as f:
                yaml_content = f.read()
        else:
            return jsonify({"error": f"拉取失败且无缓存"}), 500
    # 4. 解析 YAML 并转换
    try:
        try:
            clash_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as ye:
            return (
                jsonify(
                    {
                        "error": f"YAML 解析失败: {str(ye)}",
                        "preview": yaml_content[:100],
                    }
                ),
                400,
            )
        if not isinstance(clash_data, dict) or "proxies" not in clash_data:
            return jsonify({"error": "无效的 Clash 配置"}), 400

        raw_proxies = clash_data["proxies"]
        nodes = []
        for proxy in raw_proxies:
            try:
                original_name = proxy.get("name", "")

                # 【新增】Step 1: 优先进行黑名单排除
                # 必须在清洗前判断，否则"剩余流量"清洗后变空，可能被错误保留
                if any(ex in original_name for ex in NODE_EXCLUDE_KEYWORDS):
                    continue

                # 【新增】Step 2: 清洗节点名称
                proxy["name"] = clean_node_name(original_name)

                # Step 3: 转换为 Sing-box 格式
                sb_node = clash_to_singbox(proxy)
                if sb_node:
                    nodes.append(sb_node)
            except Exception:
                continue

        if not nodes:
            return jsonify({"error": "没有转换成功的节点"}), 400

        # 5. 模板加载与合并
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

        # 6. 关键词过滤 (白名单检查)
        # 注意：这里的过滤是基于【清洗后】的名字进行的
        def node_tag_valid(tag: str) -> bool:
            tag_upper = tag.upper() if tag else ""
            if not any(region.upper() in tag_upper for region in NODE_REGION_KEYWORDS):
                return False
            # 这里的 Exclude 检查作为兜底，虽然上面循环里已经检查过了
            if any(exclude in tag for exclude in NODE_EXCLUDE_KEYWORDS):
                return False
            return True

        filtered_outbounds = [
            o
            for o in outbounds
            if node_tag_valid(o.get("tag", ""))
            or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]
        ]
# 7. 策略组处理
        
        # --- 第一步：处理正则过滤 (删除无节点生成的动态分组) ---
        temp_outbounds = []
        
        # 提取所有基础节点 Tag (保持原有顺序，供正则匹配使用)
        all_node_tags = [
            o.get("tag")
            for o in filtered_outbounds
            if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]
        ]

        for outbound in filtered_outbounds:
            # 检查是否为动态策略组
            if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
                regex_list = [
                    reg
                    for f in outbound.get("filter", [])
                    for reg in f.get("regex", [])
                ]
                del outbound["filter"]  # 清理字段
                
                if not regex_list:
                    continue # 无规则则跳过

                pattern = "|".join(regex_list)
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    # 匹配基础节点
                    matched_tags = [
                        tag for tag in all_node_tags if compiled.search(tag)
                    ]
                    
                    if matched_tags:
                        outbound["outbounds"] = matched_tags
                        temp_outbounds.append(outbound)
                    # else: 匹配为空，不加入 temp_outbounds (即删除该国家/地区分组)
                except re.error as e:
                    print(f"无效的正则表达式 '{pattern}': {e}", file=sys.stderr)
            else:
                # 静态分组或普通节点，进入待处理列表
                temp_outbounds.append(outbound)

        # --- 第二步：清洗引用链 (如果子分组被删，父分组也要清理对应引用) ---
        final_outbounds = []
        
        # 获取第一步后幸存的所有 Tag (包括节点和分组)，用于白名单校验
        surviving_tags = {o.get("tag") for o in temp_outbounds if o.get("tag")}
        # 补充 Sing-box 内置/保留 Tag，防止误删
        BUILT_IN_TAGS = {"DIRECT", "direct", "BLOCK", "block", "DNS", "dns-out", "NOOP", "noop"}

        for outbound in temp_outbounds:
            # 如果该项有子引用列表 (outbounds 字段)
            if "outbounds" in outbound and isinstance(outbound["outbounds"], list):
                original_refs = outbound["outbounds"]
                # 过滤引用：只保留 幸存Tag 或 内置Tag
                cleaned_refs = [
                    tag for tag in original_refs 
                    if tag in surviving_tags or tag in BUILT_IN_TAGS
                ]
                
                outbound["outbounds"] = cleaned_refs
                
                # 如果清洗后列表为空，则删除该父分组 (满足 "如果为空也要删除" 的要求)
                if not cleaned_refs:
                    # print(f"分组 {outbound.get('tag')} 引用为空，已移除", file=sys.stderr)
                    continue 
            
            final_outbounds.append(outbound)

        base_config["outbounds"] = final_outbounds
        print(f"[{source}] 处理完成，返回 {len(new_nodes)} 个新节点")
        json_str = json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))
        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=config.json"},
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"服务器内部错误: {str(e)}", "source": source}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
