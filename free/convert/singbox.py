import json
import logging
import os
import re
import time
from typing import Any, Dict, Union
import requests
import yaml

logger = logging.getLogger(__name__)

# ================= [Sing-box] 专用配置 =================
SB_TEMPLATE_MAP = {
    "openwrt": "json/openwrt.json",
    "pc": "json/pc.json",
    "mtun": "json/mtun.json",
    "m": "json/m.json",
}


def process_shadowsocks_sb(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "shadowsocks"
    node["server_port"] = int(proxy["port"])
    node["method"] = proxy.get("cipher")
    node["password"] = proxy.get("password")
    if "plugin" in proxy:
        plugin = proxy.get("plugin")
        plugin_opts = proxy.get("plugin-opts", {})
        if plugin == "obfs":
            node["plugin"] = "obfs-local"
            mode = plugin_opts.get("mode", "http")
            host = plugin_opts.get("host", "")
            node["plugin_opts"] = f"obfs={mode};obfs-host={host}"
    return node


def process_vless_sb(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "vless"
    node["server_port"] = int(proxy["port"])
    node["uuid"] = proxy.get("uuid")
    node["flow"] = proxy.get("flow", "")
    if "packet-encoding" in proxy:
        node["packet_encoding"] = proxy["packet-encoding"]
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
        tls["utls"] = {"enabled": True, "fingerprint": "firefox"}
        node["tls"] = tls
    return node


def process_hysteria2_sb(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "hysteria2"
    node["password"] = proxy.get("password")
    if "ports" in proxy:
        node["server_ports"] = proxy["ports"]
    elif "port" in proxy:
        node["server_port"] = int(proxy["port"])
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
    base_node = {"tag": proxy.get("name"), "server": proxy.get("server")}
    if p_type == "ss":
        return process_shadowsocks_sb(proxy, base_node)
    elif p_type == "vless":
        return process_vless_sb(proxy, base_node)
    elif p_type == "hysteria2":
        return process_hysteria2_sb(proxy, base_node)
    else:
        return None


def fetch_and_process_singbox(
    source: str,
    config_param: str,
    force_refresh: bool,
    url: str,
    cache_dir,
    cache_expire: int,
    shared_kw: list,
    shared_ex_kw: list,
    clean_node_fn,
):
    cache_file_path = cache_dir / f"{source}.yaml"
    yaml_content = ""
    used_cache = False

    if not force_refresh and cache_file_path.exists():
        try:
            mtime = os.path.getmtime(cache_file_path)
            if time.time() - mtime < cache_expire:
                logger.info(f"[{source}] [Sing-Box] [Loaded cache]")
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    yaml_content = f.read()
                used_cache = True
        except Exception:
            pass

    if force_refresh:
        logger.info(f"[{source}] [Sing-Box] [Received u]")

    if not used_cache:
        try:
            headers = {"User-Agent": "clash-verge"}
            logger.info(f"[{source}] [Sing-Box] [Fetching ...]")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            temp_content = response.text.strip()
            if "proxies:" not in temp_content:
                raise ValueError("[Invalid Clash YAML Content]")

            yaml_content = temp_content
            with open(cache_file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            logger.info(f"[{source}] [Sing-Box] [Updated Successfully]")

        except Exception as e:
            logger.error(f"[{source}] [Sing-Box] [Error] [Loaded cache] {e}")
            if cache_file_path.exists():
                logger.warning(f"[{source}] [Sing-Box] 使用过期缓存兜底")
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    yaml_content = f.read()
            else:
                raise RuntimeError(f"[{source}] [Fetch Error]")

    try:
        clash_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as ye:
        raise ValueError(f"YAML 解析失败: {str(ye)}")

    if not isinstance(clash_data, dict) or "proxies" not in clash_data:
        raise ValueError("无效的 Clash 配置")

    raw_proxies = clash_data["proxies"]
    nodes = []
    for proxy in raw_proxies:
        try:
            original_name = proxy.get("name", "")
            if any(ex in original_name for ex in shared_ex_kw):
                continue

            proxy["name"] = clean_node_fn(original_name)
            sb_node = clash_to_singbox(proxy)
            if sb_node:
                nodes.append(sb_node)
        except Exception:
            continue

    if not nodes:
        raise ValueError("没有转换成功的节点")

    template_filename = SB_TEMPLATE_MAP.get(config_param, SB_TEMPLATE_MAP["openwrt"])
    if not os.path.exists(template_filename):
        raise FileNotFoundError(f"模板文件未找到: {template_filename}")

    with open(template_filename, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    outbounds = base_config.get("outbounds", [])
    existing_tags = {o.get("tag") for o in outbounds}
    new_nodes = [n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags]
    outbounds.extend(new_nodes)

    def node_tag_valid(tag: str) -> bool:
        tag_upper = tag.upper() if tag else ""
        if not any(region.upper() in tag_upper for region in shared_kw):
            return False
        if any(exclude in tag for exclude in shared_ex_kw):
            return False
        return True

    filtered_outbounds = [
        o
        for o in outbounds
        if node_tag_valid(o.get("tag", ""))
        or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]
    ]

    temp_outbounds = []
    all_node_tags = [
        o.get("tag")
        for o in filtered_outbounds
        if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]
    ]

    for outbound in filtered_outbounds:
        if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
            regex_list = [
                reg for f in outbound.get("filter", []) for reg in f.get("regex", [])
            ]
            del outbound["filter"]
            if not regex_list:
                continue
            pattern = "|".join(regex_list)
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                matched_tags = [tag for tag in all_node_tags if compiled.search(tag)]
                if matched_tags:
                    # 获取原有的 outbounds 列表
                    original_outbounds = outbound.get("outbounds", [])

                    # 如果有 {all} 占位符，将其移除
                    if "{all}" in original_outbounds:
                        original_outbounds.remove("{all}")

                    # 将原有策略组和新匹配的节点合并，并用 dict.fromkeys 去重
                    merged_outbounds = list(
                        dict.fromkeys(original_outbounds + matched_tags)
                    )
                    outbound["outbounds"] = merged_outbounds

                    temp_outbounds.append(outbound)
            except re.error as e:
                logger.error(f"无效的正则表达式: {e}")
        else:
            temp_outbounds.append(outbound)

    final_outbounds = []
    surviving_tags = {o.get("tag") for o in temp_outbounds if o.get("tag")}

    for outbound in temp_outbounds:
        if "outbounds" in outbound and isinstance(outbound["outbounds"], list):
            original_refs = outbound["outbounds"]
            cleaned_refs = [tag for tag in original_refs if tag in surviving_tags]
            outbound["outbounds"] = cleaned_refs
            if not cleaned_refs:
                continue
        final_outbounds.append(outbound)

    for outbound in final_outbounds:
        if outbound.get("type") == "selector":
            current_outbounds = outbound.get("outbounds", [])
            current_default = outbound.get("default", "")
            if current_outbounds and current_default not in current_outbounds:
                outbound["default"] = current_outbounds[0]

    base_config["outbounds"] = final_outbounds
    return json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))
