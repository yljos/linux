import io
import logging
import os
import re
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote
import requests
import yaml
from flask import send_file, abort

logger = logging.getLogger(__name__)

CLASH_USER_AGENT = "clash-verge"
CLASH_INCLUDED_HEADERS = ["Subscription-Userinfo"]
CLASH_FINGERPRINT = "firefox"

def save_headers_to_disk(source_name: str, headers: dict, cache_dir: Path) -> dict:
    try:
        filtered = {k: v for k, v in headers.items() if k.lower() in {h.lower() for h in CLASH_INCLUDED_HEADERS}}
        if not filtered: return {}
        with open(cache_dir / f"{source_name}.headers.json", "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, separators=(",", ":"))
        return filtered
    except Exception as e:
        logger.error(f"Save headers error: {e}")
        return {}

def load_headers_from_disk(source_name: str, cache_dir: Path) -> dict:
    p = cache_dir / f"{source_name}.headers.json"
    if not p.exists(): return {}
    with open(p, "r", encoding="utf-8") as f: return json.load(f)

def is_valid_clash_yaml(text: str) -> bool:
    return bool(text and "proxies:" in text)

def filter_node_names_clash(proxies: List[Any], shared_kw: List[str], shared_ex_kw: List[str]) -> Tuple[List[str], List[str]]:
    all_names = [str(p.get("name")) for p in proxies if isinstance(p, dict) and isinstance(p.get("name"), str)]
    valid_kw = [str(kw).lower() for kw in shared_kw if isinstance(kw, str)]
    valid_ex_kw = [str(ex).lower() for ex in shared_ex_kw if isinstance(ex, str)]
    filtered = [n for n in all_names if any(kw in n.lower() for kw in valid_kw) and not any(ex in n.lower() for ex in valid_ex_kw)]
    return filtered, all_names

def process_proxy_config_clash(proxy: Dict[str, Any], up_pref: str, down_pref: str):
    if not isinstance(proxy, dict): return
    p_type = proxy.get("type")
    up_pref, down_pref = str(up_pref or "100"), str(down_pref or "100")
    if p_type == "hysteria2":
        proxy.update({"up": up_pref if "bps" in up_pref.lower() else f"{up_pref} Mbps", "down": down_pref if "bps" in down_pref.lower() else f"{down_pref} Mbps", "skip-cert-verify": False})
    elif p_type == "vless":
        proxy.update({"skip-cert-verify": False, "packet-encoding": "xudp"})
        if "client-fingerprint" in proxy: proxy["client-fingerprint"] = CLASH_FINGERPRINT

def fetch_yaml_text_clash(url: str, source_name: str, force_refresh: bool, cache_dir: Path, cache_expire: int):
    cache_file = cache_dir / f"{source_name}.yaml"
    if not force_refresh and cache_file.exists():
        try:
            if time.time() - os.path.getmtime(cache_file) < cache_expire:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return f.read(), load_headers_from_disk(source_name, cache_dir)
        except Exception: pass
    
    try:
        res = requests.get(url, headers={"User-Agent": CLASH_USER_AGENT}, timeout=15)
        res.raise_for_status()
        text_content = res.text.lstrip("\ufeff").replace("\r\n", "\n")
        if is_valid_clash_yaml(text_content):
            save_headers_to_disk(source_name, res.headers, cache_dir)
            with open(cache_file, "w", encoding="utf-8") as f: f.write(text_content)
            return text_content, res.headers
    except Exception as e:
        logger.error(f"Fetch Error: {e}")
        
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read(), load_headers_from_disk(source_name, cache_dir)
    raise RuntimeError("Fetch and cache failed")

def process_yaml_content_clash(yaml_text: str, template_path: Path, up_pref: str, down_pref: str, shared_kw: list, shared_ex_kw: list, clean_node_fn):
    input_data = yaml.safe_load(yaml_text)
    if not isinstance(input_data, dict): raise ValueError("Invalid YAML")
    
    with open(template_path, "r", encoding="utf-8") as f: template_data = yaml.safe_load(f)
    proxies_orig = input_data.get("proxies", [])
    filtered_names, _ = filter_node_names_clash(proxies_orig, shared_kw, shared_ex_kw)
    
    final_proxies = []
    for p in proxies_orig:
        if isinstance(p, dict) and p.get("name") in filtered_names:
            p["name"] = clean_node_fn(p["name"])
            process_proxy_config_clash(p, up_pref, down_pref)
            final_proxies.append(p)
            
    if not final_proxies and proxies_orig:
        for p in proxies_orig:
            if isinstance(p, dict):
                p["name"] = clean_node_fn(p.get("name", ""))
                process_proxy_config_clash(p, up_pref, down_pref)
        final_proxies = proxies_orig
        
    final_proxies.append({"name": "dns-out", "type": "dns"})
    template_data["proxies"] = final_proxies
    
    if "proxy-groups" in template_data:
        all_node_names = [p["name"] for p in final_proxies]
        temp_groups = []
        for group in template_data["proxy-groups"]:
            if "filter" in group:
                existing = group.get("proxies", [])
                pattern = group.pop("filter")
                group.pop("include-all-proxies", None)
                try:
                    matcher = re.compile(pattern, re.IGNORECASE)
                    matched = [n for n in all_node_names if matcher.search(n)]
                    group["proxies"] = existing + [n for n in matched if n not in existing]
                except Exception: pass
                if group.get("proxies"): temp_groups.append(group)
            else: temp_groups.append(group)
            
        final_groups = []
        surviving = {g["name"] for g in temp_groups if "name" in g}
        valid_targets = set(all_node_names) | surviving | {"DIRECT", "REJECT", "PASS", "REJECT-DROP", "GCP-outbound"}
        for group in temp_groups:
            refs = [r for r in group.get("proxies", []) if r in valid_targets]
            if refs:
                group["proxies"] = refs
                final_groups.append(group)
        template_data["proxy-groups"] = final_groups
        
    return yaml.dump(template_data, allow_unicode=True, sort_keys=False, default_flow_style=False, width=4096).encode("utf-8")

def inject_custom_clash_node(yaml_bytes: bytes, node_path: Path) -> bytes:
    if not node_path.exists(): return yaml_bytes
    try:
        with open(node_path, "r", encoding="utf-8") as f: custom_data = yaml.safe_load(f)
        if not custom_data: return yaml_bytes
        nodes = custom_data if isinstance(custom_data, list) else [custom_data]
        config = yaml.safe_load(yaml_bytes)
        for node in nodes:
            if isinstance(node, dict) and "name" in node:
                config.setdefault("proxies", []).append(node)
        return yaml.safe_dump(config, allow_unicode=True, sort_keys=False).encode("utf-8")
    except Exception as e:
        logger.error(f"[Clash] Inject Error: {e}")
        return yaml_bytes

def handle_request(source, url, ua, is_force_refresh, cache_dir, cache_expire, shared_kw, shared_ex_kw, clean_fn, custom_node_path, target_groups, inject_templates, base_dir):
    clash_config_val = None
    if "ClashMetaForAndroid" in ua: clash_config_val = "mtun"
    elif "clash_pc" in ua: clash_config_val = "pc"
    elif "clash_openwrt" in ua: clash_config_val = "openwrt"
    elif "clash_m" in ua: clash_config_val = "m"
    else: abort(404)

    config_map = {
        "m": (base_dir / "yaml/m.yaml", "30 Mbps", "60 Mbps"),
        "mtun": (base_dir / "yaml/mtun.yaml", "30 Mbps", "60 Mbps"),
        "pc": (base_dir / "yaml/pc.yaml", "50 Mbps", "200 Mbps"),
        "openwrt": (base_dir / "yaml/openwrt.yaml", "50 Mbps", "200 Mbps"),
    }
    template_path, up, down = config_map[clash_config_val]

    try:
        yaml_text, headers_data = fetch_yaml_text_clash(unquote(url), source, is_force_refresh, cache_dir, cache_expire)
        output_bytes = process_yaml_content_clash(yaml_text, template_path, up, down, shared_kw, shared_ex_kw, clean_fn)
        
        if clash_config_val in inject_templates:
            output_bytes = inject_custom_clash_node(output_bytes, custom_node_path)
        
        response = send_file(io.BytesIO(output_bytes), mimetype="text/yaml", as_attachment=True, download_name="config.yaml")
        if headers_data:
            for h, v in headers_data.items():
                if h.lower() in {ih.lower() for ih in CLASH_INCLUDED_HEADERS}: response.headers[h] = v
        return response
    except Exception as e:
        logger.error(f"Clash Error: {e}")
        return str(e), 500