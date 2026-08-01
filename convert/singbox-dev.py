import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Union
import requests
import yaml
from flask import Response, jsonify

logger = logging.getLogger(__name__)

SB_TEMPLATE_MAP = {
    "openwrt": "json/openwrt.json",
    "pc": "json/pc.json",
    "mtun": "json/mtun.json",
    "m": "json/m.json",
}

def process_shadowsocks_sb(proxy: Dict[str, Any], base_node: Dict[str, Any]) -> Dict[str, Any]:
    node = base_node.copy()
    node.update({"type": "shadowsocks", "server_port": int(proxy["port"]), "method": proxy.get("cipher"), "password": proxy.get("password")})
    if "plugin" in proxy and proxy["plugin"] == "obfs":
        opts = proxy.get("plugin-opts", {})
        node.update({"plugin": "obfs-local", "plugin_opts": f"obfs={opts.get('mode', 'http')};obfs-host={opts.get('host', '')}"})
    return node

def process_vless_sb(proxy: Dict[str, Any], base_node: Dict[str, Any]) -> Dict[str, Any]:
    node = base_node.copy()
    node.update({"type": "vless", "server_port": int(proxy["port"]), "uuid": proxy.get("uuid"), "flow": proxy.get("flow", "")})
    if "packet-encoding" in proxy: node["packet_encoding"] = proxy["packet-encoding"]
    net = proxy.get("network", "tcp")
    if net == "ws":
        ws = proxy.get("ws-opts", {})
        node["transport"] = {"type": "ws", "path": ws.get("path", "/")}
        if "headers" in ws and "Host" in ws["headers"]: node["transport"]["headers"] = {"Host": ws["headers"]["Host"]}
    elif net == "grpc":
        node["transport"] = {"type": "grpc", "service_name": proxy.get("grpc-opts", {}).get("grpc-service-name", "")}
    if proxy.get("tls") or proxy.get("reality-opts"):
        tls = {"enabled": True, "insecure": proxy.get("skip-cert-verify", False), "server_name": proxy.get("servername", ""), "utls": {"enabled": True, "fingerprint": "firefox"}}
        if "reality-opts" in proxy:
            ro = proxy.get("reality-opts", {})
            tls["reality"] = {"enabled": True, "public_key": ro.get("public-key"), "short_id": ro.get("short-id")}
            if not tls["server_name"]: tls["server_name"] = proxy.get("sni", "")
        node["tls"] = tls
    return node

def process_hysteria2_sb(proxy: Dict[str, Any], base_node: Dict[str, Any]) -> Dict[str, Any]:
    node = base_node.copy()
    node.update({"type": "hysteria2", "password": proxy.get("password"), "up_mbps": 50, "down_mbps": 200})
    if "ports" in proxy: node["server_ports"] = str(proxy["ports"]).replace("-", ":")
    elif "port" in proxy:
        pv = str(proxy["port"])
        if "-" in pv: node["server_ports"] = pv.replace("-", ":")
        else: node["server_port"] = int(proxy["port"])
    if "obfs" in proxy: node["obfs"] = {"type": "salamander", "password": proxy.get("obfs-password", "")}
    node["tls"] = {"enabled": True, "insecure": proxy.get("skip-cert-verify", False), "server_name": proxy.get("sni", "")}
    return node

def clash_to_singbox(proxy: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    ptype = proxy.get("type", "").lower()
    base = {"tag": proxy.get("name"), "server": proxy.get("server")}
    if ptype == "ss": return process_shadowsocks_sb(proxy, base)
    if ptype == "vless": return process_vless_sb(proxy, base)
    if ptype == "hysteria2": return process_hysteria2_sb(proxy, base)
    return None

def fetch_and_process_singbox(source: str, config_param: str, force_refresh: bool, url: str, cache_dir: Path, cache_expire: int, shared_kw: list, shared_ex_kw: list, clean_node_fn):
    cache_file = cache_dir / f"{source}.yaml"
    used_cache = False
    if not force_refresh and cache_file.exists():
        try:
            if time.time() - os.path.getmtime(cache_file) < cache_expire:
                with open(cache_file, "r", encoding="utf-8") as f: yaml_content = f.read()
                used_cache = True
        except Exception: pass
        
    if not used_cache:
        try:
            res = requests.get(url, headers={"User-Agent": "clash-verge"}, timeout=10)
            res.raise_for_status()
            yaml_content = res.text.strip()
            if "proxies:" not in yaml_content: raise ValueError("Invalid YAML")
            with open(cache_file, "w", encoding="utf-8") as f: f.write(yaml_content)
        except Exception:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f: yaml_content = f.read()
            else: raise RuntimeError("Fetch Error")
            
    clash_data = yaml.safe_load(yaml_content)
    if not isinstance(clash_data, dict) or "proxies" not in clash_data: raise ValueError("Invalid Config")
    
    nodes = []
    for proxy in clash_data["proxies"]:
        try:
            name = proxy.get("name", "")
            if any(ex in name for ex in shared_ex_kw): continue
            proxy["name"] = clean_node_fn(name)
            sb_node = clash_to_singbox(proxy)
            if sb_node: nodes.append(sb_node)
        except Exception: pass
    if not nodes: raise ValueError("No nodes converted")

    with open(SB_TEMPLATE_MAP.get(config_param, SB_TEMPLATE_MAP["openwrt"]), "r", encoding="utf-8") as f: 
        base_config = json.load(f)
        
    outbounds = base_config.get("outbounds", [])
    existing_tags = {o.get("tag") for o in outbounds}
    outbounds.extend([n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags])

    def valid_tag(tag: str) -> bool:
        tu = tag.upper() if tag else ""
        return any(kw.upper() in tu for kw in shared_kw) and not any(ex.upper() in tu for ex in shared_ex_kw)

    filtered = [o for o in outbounds if valid_tag(o.get("tag", "")) or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]]
    temp_outbounds = []
    all_tags = [o.get("tag") for o in filtered if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]]

    for outbound in filtered:
        if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
            regex_list = [reg for f in outbound.pop("filter", []) if isinstance(f, dict) for reg in f.get("regex", [])]
            orig_out = outbound.get("outbounds", [])
            if "{all}" in orig_out: orig_out.remove("{all}")
            
            if not regex_list:
                if orig_out:
                    outbound["outbounds"] = list(dict.fromkeys(orig_out))
                    temp_outbounds.append(outbound)
                continue
                
            try:
                compiled = re.compile("|".join(regex_list), re.IGNORECASE)
                matched = [t for t in all_tags if compiled.search(t)]
                merged = list(dict.fromkeys(orig_out + matched))
                if merged:
                    outbound["outbounds"] = merged
                    temp_outbounds.append(outbound)
            except Exception:
                if orig_out:
                    outbound["outbounds"] = list(dict.fromkeys(orig_out))
                    temp_outbounds.append(outbound)
        else: temp_outbounds.append(outbound)

    final_outbounds = []
    surviving = {o.get("tag") for o in temp_outbounds if o.get("tag")}
    for outbound in temp_outbounds:
        if "outbounds" in outbound and isinstance(outbound["outbounds"], list):
            cleaned = [t for t in outbound["outbounds"] if t in surviving]
            outbound["outbounds"] = cleaned
            if not cleaned: continue
        final_outbounds.append(outbound)

    for outbound in final_outbounds:
        if outbound.get("type") == "selector":
            outs = outbound.get("outbounds", [])
            if outs and outbound.get("default", "") not in outs: outbound["default"] = outs[0]

    base_config["outbounds"] = final_outbounds
    return json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))

def inject_custom_singbox_node(json_str: str, node_path: Path, target_groups: list) -> str:
    if not node_path.exists(): return json_str
    try:
        with open(node_path, "r", encoding="utf-8") as f: custom_data = json.load(f)
        if not custom_data: return json_str
        outbounds = custom_data if isinstance(custom_data, list) else [custom_data]
        config = json.loads(json_str)
        for outbound in outbounds:
            if isinstance(outbound, dict) and "tag" in outbound:
                node_tag = outbound["tag"]
                config.setdefault("outbounds", []).append(outbound)
                for cfg_outbound in config.get("outbounds", []):
                    if cfg_outbound.get("tag") in target_groups and cfg_outbound.get("type") in ["selector", "urltest"]:
                        cfg_outbound.setdefault("outbounds", []).append(node_tag)
        return json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        logger.error(f"[Sing-box] Inject Error: {e}")
        return json_str

def handle_request(source, url, ua, is_force_refresh, cache_dir, cache_expire, shared_kw, shared_ex_kw, clean_fn, custom_node_path, target_groups, inject_templates):
    singbox_ua_map = {"SFA": "mtun", "sing-box_openwrt": "openwrt", "sing-box_m": "m", "sing-box_pc": "pc"}
    config_val = next((v for k, v in singbox_ua_map.items() if k in ua), None)
    if not config_val: return jsonify({"error": "No matching Sing-box UA"}), 404

    try:
        json_str = fetch_and_process_singbox(source, config_val, is_force_refresh, url, cache_dir, cache_expire, shared_kw, shared_ex_kw, clean_fn)
        
        if config_val in inject_templates:
            json_str = inject_custom_singbox_node(json_str, custom_node_path, target_groups)
            
        return Response(json_str, mimetype="application/json", headers={"Content-Disposition": "attachment; filename=config.json"})
    except Exception as e:
        logger.error(f"Singbox Error: {e}")
        return jsonify({"error": str(e)}), 500