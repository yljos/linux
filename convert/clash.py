import io
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import unquote

import requests
import yaml
from flask import send_file, abort

logger = logging.getLogger(__name__)

# Update User-Agent to clash-verge for fetching YAML directly
CLASH_USER_AGENT = "clash-verge"
CLASH_FINGERPRINT = "firefox"

# ================= Clash Processors =================
class FlowDict(dict):
    pass


def flow_representer(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)


yaml.add_representer(FlowDict, flow_representer)


# Recursively apply FlowDict only to dictionaries inside lists
def process_data(data):
    if isinstance(data, dict):
        return {k: process_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [
            (
                FlowDict({k: process_data(v) for k, v in i.items()})
                if isinstance(i, dict)
                else process_data(i)
            )
            for i in data
        ]
    return data


def process_proxy_config_clash(proxy: Dict[str, Any], up_pref: str, down_pref: str):
    if not isinstance(proxy, dict):
        return
    p_type = proxy.get("type")
    up_pref, down_pref = str(up_pref or "100"), str(down_pref or "100")
    if p_type == "hysteria2":
        proxy.update(
            {
                "up": up_pref if "bps" in up_pref.lower() else f"{up_pref} Mbps",
                "down": (
                    down_pref if "bps" in down_pref.lower() else f"{down_pref} Mbps"
                ),
            }
        )
        proxy.pop("skip-cert-verify", None)
    elif p_type == "vless":
        proxy.update({"packet-encoding": "xudp"})
        proxy.pop("skip-cert-verify", None)
        if "client-fingerprint" in proxy:
            proxy["client-fingerprint"] = CLASH_FINGERPRINT


def fetch_remote_yaml(
    url: str, source_name: str, force_refresh: bool, cache_dir: Path, cache_expire: int
) -> Tuple[str, str]:
    # Cache raw YAML content and userinfo
    cache_file = cache_dir / f"{source_name}.yaml"
    info_file = cache_dir / f"{source_name}.info"

    # Check cache
    if not force_refresh and cache_file.exists():
        try:
            if time.time() - os.path.getmtime(cache_file) < cache_expire:
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw_yaml = f.read()
                userinfo = ""
                if info_file.exists():
                    with open(info_file, "r", encoding="utf-8") as f:
                        userinfo = f.read().strip()
                return raw_yaml, userinfo
        except Exception:
            pass

    # Fetch remote
    try:
        res = requests.get(url, headers={"User-Agent": CLASH_USER_AGENT}, timeout=15)
        res.raise_for_status()

        raw_yaml = res.text
        userinfo = res.headers.get("Subscription-Userinfo", "")

        # Update cache
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(raw_yaml)
        if userinfo:
            with open(info_file, "w", encoding="utf-8") as f:
                f.write(userinfo)

        return raw_yaml, userinfo
    except Exception as e:
        logger.error(f"Fetch Error: {e}")

    # Fallback to cache if fetch fails
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            raw_yaml = f.read()
        userinfo = ""
        if info_file.exists():
            with open(info_file, "r", encoding="utf-8") as f:
                userinfo = f.read().strip()
        return raw_yaml, userinfo
    raise RuntimeError("Fetch and cache failed")


def process_yaml_content_clash(
    remote_yaml_text: str,
    template_path: Path,
    mixin_paths: list,
    up_pref: str,
    down_pref: str,
    clean_node_fn,
):
    # Parse the remote YAML configuration directly
    try:
        input_data = yaml.safe_load(remote_yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse remote YAML: {e}")

    if not isinstance(input_data, dict) or not input_data.get("proxies"):
        preview = remote_yaml_text[:100].replace("\n", " ") if remote_yaml_text else "Empty content"
        raise ValueError(f"No valid proxies found in remote YAML. Preview: {preview}")

    # Load base config.yaml
    with open(template_path, "r", encoding="utf-8") as f:
        template_data = yaml.safe_load(f)
        
    # Merge mixin configurations
    for m_path in mixin_paths:
        if m_path.exists():
            with open(m_path, "r", encoding="utf-8") as f:
                m_data = yaml.safe_load(f)
                if isinstance(m_data, dict):
                    template_data.update(m_data)

    proxies_orig = input_data.get("proxies", [])
    final_proxies = []
    
    # Inject all nodes without filtering
    for p in proxies_orig:
        if isinstance(p, dict):
            p["name"] = clean_node_fn(p.get("name", ""))
            process_proxy_config_clash(p, up_pref, down_pref)
            final_proxies.append(p)

    # Add dns-out directly
    final_proxies.append({"name": "dns-out", "type": "dns"})
    template_data["proxies"] = final_proxies

    processed_data = process_data(template_data)
    return yaml.dump(
        processed_data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=float("inf"),
    ).encode("utf-8")


def inject_custom_clash_node(yaml_bytes: bytes, node_path: Path) -> bytes:
    if not node_path.exists():
        return yaml_bytes
    try:
        with open(node_path, "r", encoding="utf-8") as f:
            custom_data = yaml.safe_load(f)
        if not custom_data:
            return yaml_bytes
        nodes = custom_data if isinstance(custom_data, list) else [custom_data]
        config = yaml.safe_load(yaml_bytes)
        for node in nodes:
            if isinstance(node, dict) and "name" in node:
                config.setdefault("proxies", []).append(node)

        processed_data = process_data(config)
        return yaml.dump(
            processed_data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=float("inf"),
        ).encode("utf-8")
    except Exception as e:
        logger.error(f"[Clash] Inject Error: {e}")
        return yaml_bytes


# ================= FINAL FORMATTING =================
class FinalFlowDict(dict):
    pass


class FinalFlowList(list):
    pass


def final_flow_mapping_representer(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)


def final_flow_sequence_representer(dumper, data):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.add_representer(FinalFlowDict, final_flow_mapping_representer)
yaml.add_representer(FinalFlowList, final_flow_sequence_representer)


def final_format_data(data, level=0):
    if isinstance(data, dict):
        if level > 0 and all(not isinstance(v, (dict, list)) for v in data.values()):
            return FinalFlowDict(
                {k: final_format_data(v, level + 1) for k, v in data.items()}
            )
        return {k: final_format_data(v, level + 1) for k, v in data.items()}

    elif isinstance(data, list):
        if len(data) == 0:
            return FinalFlowList([])

        if all(isinstance(i, dict) for i in data):
            return [
                FinalFlowDict(
                    {k: final_format_data(v, level + 1) for k, v in i.items()}
                )
                for i in data
            ]

        if level <= 1:
            return [final_format_data(i, level + 1) for i in data]

        if all(not isinstance(i, (dict, list)) for i in data):
            return FinalFlowList([final_format_data(i, level + 1) for i in data])

        return [final_format_data(i, level + 1) for i in data]

    return data


# ====================================================

def handle_request(
    source,
    url,
    ua,
    is_force_refresh,
    cache_dir,
    cache_expire,
    clean_fn,
    custom_node_path,
    target_groups,
    inject_templates,
    base_dir,
):
    clash_config_val = None
    mixin_paths = []
    
    # Base config is always config.yaml
    template_path = base_dir / "yaml/config.yaml"
    
    # Determine routing and add specific mixin files
    if "clash_tun" in ua or "ClashMetaForAndroid" in ua:
        clash_config_val = "tun"
        mixin_paths.append(base_dir / "yaml/tun.yaml")
    elif "clash_openwrt" in ua:
        clash_config_val = "openwrt"
        mixin_paths.append(base_dir / "yaml/tproxy.yaml")
    elif any(k in ua for k in ["clash_pc", "clash_m"]) or "clash" in ua.lower():
        clash_config_val = "standard"
    else:
        abort(404)

    up, down = "50 Mbps", "100 Mbps"

    try:
        # Extract dynamic header from fetch_remote_yaml
        remote_yaml_text, userinfo_header = fetch_remote_yaml(
            unquote(url), source, is_force_refresh, cache_dir, cache_expire
        )
        
        # Process the configuration with mixins and all nodes injected
        output_bytes = process_yaml_content_clash(
            remote_yaml_text, template_path, mixin_paths, up, down, clean_fn
        )

        if clash_config_val in inject_templates:
            output_bytes = inject_custom_clash_node(output_bytes, custom_node_path)

        final_config = yaml.safe_load(output_bytes)
        formatted_config = final_format_data(final_config)
        output_bytes = yaml.dump(
            formatted_config,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=float("inf"),
        ).encode("utf-8")

        response = send_file(
            io.BytesIO(output_bytes),
            mimetype="text/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )

        # Set dynamic header if it exists
        if userinfo_header:
            response.headers["Subscription-Userinfo"] = userinfo_header

        return response
    except Exception as e:
        logger.error(f"Clash Error: {e}")
        return str(e), 500