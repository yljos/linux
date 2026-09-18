import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Union
from urllib.parse import urlparse, parse_qs, unquote
import requests
from flask import Response, jsonify

logger = logging.getLogger(__name__)

SB_TEMPLATE_MAP = {
    "openwrt": "json/openwrt.json",
    "pc": "json/pc.json",
    "mtun": "json/mtun.json",
    "m": "json/m.json",
}


def safe_b64decode(s: str) -> str:
    # Compatible with urlsafe and standard base64 decoding
    s = s.strip()
    s += "=" * ((4 - len(s) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(s).decode("utf-8")
    except Exception:
        return base64.b64decode(s).decode("utf-8")


# ================= URI Parsers =================
def parse_ss(uri: str) -> dict:
    uri, name = uri.split("#", 1) if "#" in uri else (uri, "SS Node")
    name = unquote(name)
    uri = uri[5:]  # Strip ss://

    if "@" in uri:
        user_part, host_part = uri.split("@", 1)
        user_info = safe_b64decode(user_part)
        method, pwd = user_info.split(":", 1)
        host, port = host_part.split(":", 1)
    else:
        decoded = safe_b64decode(uri)
        user_info, host_part = decoded.split("@", 1)
        method, pwd = user_info.split(":", 1)
        host, port = host_part.split(":", 1)

    return {
        "type": "shadowsocks",
        "tag": name,
        "server": host,
        "server_port": int(port),
        "method": method,
        "password": pwd,
    }


def parse_vless(uri: str) -> dict:
    parsed = urlparse(uri)
    name = unquote(parsed.fragment) if parsed.fragment else "VLESS Node"
    qs = parse_qs(parsed.query)
    node = {
        "type": "vless",
        "tag": name,
        "server": parsed.hostname,
        "server_port": parsed.port or 443,
        "uuid": parsed.username,
    }

    if "flow" in qs and qs["flow"][0]:
        node["flow"] = qs["flow"][0]

    security = qs.get("security", ["none"])[0]
    if security in ["tls", "reality"]:
        tls = {
            "enabled": True,
            "server_name": qs.get("sni", [""])[0],
            "utls": {"enabled": True, "fingerprint": "firefox"},
        }
        if security == "reality":
            tls["reality"] = {
                "enabled": True,
                "public_key": qs.get("pbk", [""])[0],
                "short_id": qs.get("sid", [""])[0],
            }
        node["tls"] = tls
    net = qs.get("type", ["tcp"])[0]
    if net == "ws":
        node["transport"] = {"type": "ws", "path": qs.get("path", ["/"])[0]}
        if "host" in qs:
            node["transport"]["headers"] = {"Host": qs["host"][0]}
    elif net == "grpc":
        node["transport"] = {
            "type": "grpc",
            "service_name": qs.get("serviceName", [""])[0],
        }

    return node


def parse_hy2(uri: str) -> dict:
    parsed = urlparse(uri)
    name = unquote(parsed.fragment) if parsed.fragment else "HY2 Node"
    qs = parse_qs(parsed.query)

    # Bypass urlparse error handling for ports containing "-"
    netloc = parsed.netloc
    host_port = netloc.split("@")[-1]
    server_port = None
    server_ports = None

    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        if "-" in port_str:
            server_ports = port_str.replace("-", ":")
        else:
            server_port = int(port_str)
    else:
        server_port = 443

    obfs = None
    if "obfs" in qs:
        obfs = {
            "type": qs["obfs"][0],
            "password": qs.get("obfs-password", [""])[0],
        }

    # Construct the dictionary in the exact requested order
    node = {
        "type": "hysteria2",
        "tag": name,
        "server": parsed.hostname,
    }

    if server_ports is not None:
        node["server_ports"] = server_ports
    else:
        node["server_port"] = server_port

    node["up_mbps"] = 50
    node["down_mbps"] = 200

    if obfs:
        node["obfs"] = obfs

    node["password"] = parsed.username
    node["tls"] = {"enabled": True, "server_name": qs.get("sni", [""])[0]}

    return node


def uri_to_singbox(uri: str) -> Union[Dict[str, Any], None]:
    try:
        if uri.startswith("ss://"):
            return parse_ss(uri)
        elif uri.startswith("vless://"):
            return parse_vless(uri)
        elif uri.startswith("hysteria2://") or uri.startswith("hy2://"):
            return parse_hy2(uri)
    except Exception as e:
        logger.warning(f"Failed to parse URI: {e}")
    return None


# ================= Main Processor =================
def fetch_and_process_singbox(
    source: str,
    config_param: str,
    force_refresh: bool,
    url: str,
    cache_dir: Path,
    cache_expire: int,
    shared_kw: list,
    shared_ex_kw: list,
    clean_node_fn,
):
    # Use .txt suffix for URI list cache
    cache_file = cache_dir / f"{source}_uris.txt"
    used_cache = False

    if not force_refresh and cache_file.exists():
        try:
            if time.time() - os.path.getmtime(cache_file) < cache_expire:
                with open(cache_file, "r", encoding="utf-8") as f:
                    # Read base64 content and decode
                    raw_b64 = f.read()
                    decoded_text = safe_b64decode(raw_b64)
                used_cache = True
        except Exception:
            pass

    if not used_cache:
        try:
            # Use real browser UA to fetch base64 subscription
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
            }
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()

            raw_b64 = res.text.strip()
            decoded_text = safe_b64decode(raw_b64)

            if not any(
                proto in decoded_text
                for proto in ["ss://", "vless://", "hysteria2://", "hy2://"]
            ):
                raise ValueError("No valid protocol URIs found in decoded text")

            # Save raw base64 content to cache
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(raw_b64)
        except Exception:
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    # Fallback to cache and decode
                    decoded_text = safe_b64decode(f.read())
            else:
                raise RuntimeError("Fetch Error")

    # Parse and assemble nodes
    lines = [line.strip() for line in decoded_text.splitlines() if line.strip()]
    nodes = []

    for uri in lines:
        try:
            node = uri_to_singbox(uri)
            if not node:
                continue

            original_name = node["tag"]
            if any(ex in original_name for ex in shared_ex_kw):
                continue
            node["tag"] = clean_node_fn(original_name)
            nodes.append(node)
        except Exception:
            pass

    if not nodes:
        raise ValueError("No nodes converted")

    with open(
        SB_TEMPLATE_MAP.get(config_param, SB_TEMPLATE_MAP["openwrt"]),
        "r",
        encoding="utf-8",
    ) as f:
        base_config = json.load(f)

    outbounds = base_config.get("outbounds", [])
    existing_tags = {o.get("tag") for o in outbounds}
    outbounds.extend(
        [n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags]
    )

    def valid_tag(tag: str) -> bool:
        tu = tag.upper() if tag else ""
        return any(kw.upper() in tu for kw in shared_kw) and not any(
            ex.upper() in tu for ex in shared_ex_kw
        )

    filtered = [
        o
        for o in outbounds
        if valid_tag(o.get("tag", ""))
        or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]
    ]
    temp_outbounds = []
    all_tags = [
        o.get("tag")
        for o in filtered
        if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]
    ]

    for outbound in filtered:
        if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
            regex_list = [
                reg
                for f in outbound.pop("filter", [])
                if isinstance(f, dict)
                for reg in f.get("regex", [])
            ]
            orig_out = outbound.get("outbounds", [])
            if "{all}" in orig_out:
                orig_out.remove("{all}")

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
        else:
            temp_outbounds.append(outbound)

    final_outbounds = []
    surviving = {o.get("tag") for o in temp_outbounds if o.get("tag")}
    for outbound in temp_outbounds:
        if "outbounds" in outbound and isinstance(outbound["outbounds"], list):
            cleaned = [t for t in outbound["outbounds"] if t in surviving]
            outbound["outbounds"] = cleaned
            if not cleaned:
                continue
        final_outbounds.append(outbound)

    for outbound in final_outbounds:
        if outbound.get("type") == "selector":
            outs = outbound.get("outbounds", [])
            if outs and outbound.get("default", "") not in outs:
                outbound["default"] = outs[0]

    base_config["outbounds"] = final_outbounds
    return json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))


def inject_custom_singbox_node(
    json_str: str, node_path: Path, target_groups: list
) -> str:
    if not node_path.exists():
        return json_str
    try:
        with open(node_path, "r", encoding="utf-8") as f:
            custom_data = json.load(f)
        if not custom_data:
            return json_str
        outbounds = custom_data if isinstance(custom_data, list) else [custom_data]
        config = json.loads(json_str)
        for outbound in outbounds:
            if isinstance(outbound, dict) and "tag" in outbound:
                node_tag = outbound["tag"]
                config.setdefault("outbounds", []).append(outbound)
                for cfg_outbound in config.get("outbounds", []):
                    if cfg_outbound.get("tag") in target_groups and cfg_outbound.get(
                        "type"
                    ) in ["selector", "urltest"]:
                        cfg_outbound.setdefault("outbounds", []).append(node_tag)
        return json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        logger.error(f"[Sing-box] Inject Error: {e}")
        return json_str


def handle_request(
    source,
    url,
    ua,
    is_force_refresh,
    cache_dir,
    cache_expire,
    shared_kw,
    shared_ex_kw,
    clean_fn,
    custom_node_path,
    target_groups,
    inject_templates,
):
    singbox_ua_map = {
        "SFA": "mtun",
        "sing-box_openwrt": "openwrt",
        "sing-box_m": "m",
        "sing-box_pc": "pc",
    }
    config_val = next((v for k, v in singbox_ua_map.items() if k in ua), None)
    if not config_val:
        return jsonify({"error": "No matching Sing-box UA"}), 404

    try:
        json_str = fetch_and_process_singbox(
            source,
            config_val,
            is_force_refresh,
            url,
            cache_dir,
            cache_expire,
            shared_kw,
            shared_ex_kw,
            clean_fn,
        )

        if config_val in inject_templates:
            json_str = inject_custom_singbox_node(
                json_str, custom_node_path, target_groups
            )

        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=config.json"},
        )
    except Exception as e:
        logger.error(f"Singbox Error: {e}")
        return jsonify({"error": str(e)}), 500
