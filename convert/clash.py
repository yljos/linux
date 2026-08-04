import base64
import io
import logging
import os
import re
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs, unquote
import requests
import yaml
from flask import send_file, abort

logger = logging.getLogger(__name__)

CLASH_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0"
CLASH_FINGERPRINT = "firefox"

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
        proxy.update({"up": up_pref if "bps" in up_pref.lower() else f"{up_pref} Mbps", "down": down_pref if "bps" in down_pref.lower() else f"{down_pref} Mbps"})
        proxy.pop("skip-cert-verify", None)
    elif p_type == "vless":
        proxy.update({"packet-encoding": "xudp"})
        proxy.pop("skip-cert-verify", None)
        if "client-fingerprint" in proxy: proxy["client-fingerprint"] = CLASH_FINGERPRINT

def parse_uris_to_proxies(text: str) -> dict:
    proxies = []
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        
        try:
            if line.startswith("vless://"):
                parsed = urlparse(line)
                uuid, server_port = parsed.netloc.split("@")
                server, port = server_port.split(":")
                qs = parse_qs(parsed.query)
                name = unquote(parsed.fragment) if parsed.fragment else f"vless-{server}"
                
                proxy = {
                    "name": name,
                    "type": "vless",
                    "server": server,
                    "port": int(port),
                    "uuid": uuid,
                    "udp": True,
                    "tls": qs.get("security", [""])[0] in ("tls", "reality")
                }
                
                if proxy["tls"]:
                    proxy["servername"] = qs.get("sni", [server])[0]
                    if "fp" in qs: proxy["client-fingerprint"] = qs["fp"][0]
                    if qs.get("security", [""])[0] == "reality":
                        proxy["reality-opts"] = {"public-key": qs.get("pbk", [""])[0]}
                        if "sid" in qs: proxy["reality-opts"]["short-id"] = qs["sid"][0]

                network = qs.get("type", ["tcp"])[0]
                proxy["network"] = network
                
                if network == "ws":
                    proxy["ws-opts"] = {
                        "path": qs.get("path", ["/"])[0],
                        "headers": {"Host": qs.get("host", [server])[0]}
                    }
                elif network == "grpc":
                    proxy["grpc-opts"] = {
                        "grpc-service-name": qs.get("serviceName", [""])[0]
                    }
                proxies.append(proxy)
                
            elif line.startswith("vmess://"):
                b64_str = line[8:]
                b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
                v_json = json.loads(base64.b64decode(b64_str).decode("utf-8"))
                proxy = {
                    "name": unquote(v_json.get("ps", f"vmess-{v_json.get('add')}")),
                    "type": "vmess",
                    "server": v_json.get("add"),
                    "port": int(v_json.get("port")),
                    "uuid": v_json.get("id"),
                    "alterId": int(v_json.get("aid", 0)),
                    "cipher": v_json.get("scy", "auto"),
                    "udp": True,
                }
                if v_json.get("tls") == "tls":
                    proxy["tls"] = True
                    if v_json.get("sni"): proxy["servername"] = v_json.get("sni")
                    if v_json.get("fp"): proxy["client-fingerprint"] = v_json.get("fp")
                    
                network = v_json.get("net", "tcp")
                proxy["network"] = network
                
                if network == "ws":
                    proxy["ws-opts"] = {
                        "path": v_json.get("path", "/"),
                        "headers": {"Host": v_json.get("host", v_json.get("add"))}
                    }
                elif network == "grpc":
                    proxy["grpc-opts"] = {
                        "grpc-service-name": v_json.get("path", "")
                    }
                proxies.append(proxy)
                
            elif line.startswith("trojan://") or line.startswith("hysteria2://"):
                parsed = urlparse(line)
                password, server_port = parsed.netloc.split("@")
                server, port = server_port.split(":")
                qs = parse_qs(parsed.query)
                name = unquote(parsed.fragment) if parsed.fragment else f"proxy-{server}"
                p_type = "trojan" if line.startswith("trojan") else "hysteria2"
                
                proxy = {
                    "name": name,
                    "type": p_type,
                    "server": server,
                    "port": int(port),
                    "password": password,
                    "udp": True,
                }
                if "sni" in qs: proxy["sni"] = qs["sni"][0]
                
                if p_type == "hysteria2":
                    if "obfs" in qs: proxy["obfs"] = qs["obfs"][0]
                    if "obfs-password" in qs: proxy["obfs-password"] = qs["obfs-password"][0]
                    
                proxies.append(proxy)
                
        except Exception as e:
            logger.warning(f"Parse Error for node {line[:30]}...: {e}")
            
    return {"proxies": proxies}

def fetch_uris_text(url: str, source_name: str, force_refresh: bool, cache_dir: Path, cache_expire: int):
    # Cache raw base64 content
    cache_file = cache_dir / f"{source_name}_uris.txt"
    
    # Helper to decode base64
    def decode_base64_content(b64_str: str) -> str:
        b64_str = re.sub(r'\s+', '', b64_str)
        b64_str = b64_str.replace("-", "+").replace("_", "/")
        padding = len(b64_str) % 4
        if padding != 0:
            b64_str += "=" * (4 - padding)
        decoded_bytes = base64.b64decode(b64_str)
        return decoded_bytes.decode("utf-8", errors="ignore").lstrip("\ufeff").replace("\r\n", "\n")

    if not force_refresh and cache_file.exists():
        try:
            if time.time() - os.path.getmtime(cache_file) < cache_expire:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return decode_base64_content(f.read())
        except Exception: pass
    
    try:
        res = requests.get(url, headers={"User-Agent": CLASH_USER_AGENT}, timeout=15)
        res.raise_for_status()
        
        raw_b64 = res.text.strip()
        
        # Save raw base64 to disk
        with open(cache_file, "w", encoding="utf-8") as f: 
            f.write(raw_b64)
            
        return decode_base64_content(raw_b64)
    except Exception as e:
        logger.error(f"Fetch Error: {e}")
        
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return decode_base64_content(f.read())
    raise RuntimeError("Fetch and cache failed")

def process_yaml_content_clash(uri_text: str, template_path: Path, up_pref: str, down_pref: str, shared_kw: list, shared_ex_kw: list, clean_node_fn, custom_node_path: Path, clash_config_val: str, inject_templates: list):
    input_data = parse_uris_to_proxies(uri_text)
        
    if not isinstance(input_data, dict) or not input_data.get("proxies"):
        preview = uri_text[:100].replace("\n", " ") if uri_text else "Empty content"
        raise ValueError(f"No valid proxies found. Decoded content preview: {preview}")
    
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
        
    # Inject custom nodes
    if clash_config_val in inject_templates and custom_node_path.exists():
        try:
            with open(custom_node_path, "r", encoding="utf-8") as f: custom_data = yaml.safe_load(f)
            if custom_data:
                nodes = custom_data if isinstance(custom_data, list) else [custom_data]
                for node in nodes:
                    if isinstance(node, dict) and "name" in node:
                        final_proxies.append(node)
        except Exception as e:
            logger.error(f"[Clash] Inject Error: {e}")

    final_proxies.append({"name": "dns-out", "type": "dns"})
    
    # Dump the proxy list to YAML string
    proxy_list_str = yaml.dump(final_proxies, allow_unicode=True, sort_keys=False, default_flow_style=False)
    
    # Indent all proxies by 2 spaces to align correctly with "proxies:"
    indented_proxies = "\n".join("  " + line for line in proxy_list_str.splitlines())
    
    # Read the template text
    with open(template_path, "r", encoding="utf-8") as f:
        template_text = f.read()
        
    # Regex to match "proxies:" or "proxies: []" preserving the template structure
    pattern = re.compile(r'^proxies:\s*(?:\[\])?\s*$', re.MULTILINE)
    
    if pattern.search(template_text):
        # Insert the indented proxy list after "proxies:"
        replacement = "proxies:\n" + indented_proxies
        output_text = pattern.sub(replacement, template_text, count=1)
    else:
        # Append to the end if "proxies:" does not exist in the template
        output_text = template_text + "\n\nproxies:\n" + indented_proxies
        
    return output_text.encode("utf-8")

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
        uri_text = fetch_uris_text(unquote(url), source, is_force_refresh, cache_dir, cache_expire)
        
        output_bytes = process_yaml_content_clash(
            uri_text, template_path, up, down, shared_kw, shared_ex_kw, clean_fn,
            custom_node_path, clash_config_val, inject_templates
        )
        
        response = send_file(io.BytesIO(output_bytes), mimetype="text/yaml", as_attachment=True, download_name="config.yaml")
        
        # upload: 666 GB, download: 999 GB, total: 999 GB (1072668082176 bytes), expire: 2030-01-01 00:00:00
        response.headers["Subscription-Userinfo"] = "upload=715112054784; download=1072668082176; total=1072668082176; expire=1893456000"
        
        return response
    except Exception as e:
        logger.error(f"Clash Error: {e}")
        return str(e), 500