import hashlib
import hmac
import io
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote

import requests
import yaml
from flask import Flask, request, abort, send_file

# ================= Config =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

CUSTOM_CLASH_NODE = BASE_DIR / "node.yaml"
TARGET_GROUPS = ["Google"]
INJECT_TEMPLATES = ["tun"]

RENAME_MAP = {"香港": "HK", "美国": "US", "新加坡": "SG", "日本": "JP", "家宽": "ISP"}
SHARED_KEYWORDS = [
    "US",
    "HK",
    "SG",
    "JP",
    "Hong Kong",
    "Singapore",
    "Japan",
    "United States",
    "美国",
    "香港",
    "新加坡",
    "日本",
]
SHARED_EXCLUDE_KEYWORDS = [
    "官网",
    "流量",
    "倍率",
    "剩余",
    "Australia",
    "到期",
    "重置",
    "HK2-HY2",
    "HK3-HY2",
    "HK4-HY2",
    "HK5-HY2",
]

# Set to any file name in the directory (e.g., "wukong", "shaseng")
ACTUAL_SOURCE = "mitce"

app = Flask(__name__)

CLASH_USER_AGENT = "clash-verge"
CLASH_FINGERPRINT = "firefox"


# ================= Utils =================
def read_url_from_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if url := line.strip():
                return url
    raise ValueError(f"URL [None]: {path}")


def clean_node_name(name: str) -> str:
    if not name:
        return name
    for k, v in RENAME_MAP.items():
        name = name.replace(k, v)
    name = re.sub(r"[^\x00-\x7F]+", "", name)
    return re.sub(r"\s+", " ", name).strip()


# ================= Clash Processors =================
class FlowDict(dict):
    pass


def flow_representer(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True)


yaml.add_representer(FlowDict, flow_representer)


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


def filter_node_names_clash(
    proxies: List[Any], shared_kw: List[str], shared_ex_kw: List[str]
) -> Tuple[List[str], List[str]]:
    all_names = [
        str(p.get("name"))
        for p in proxies
        if isinstance(p, dict) and isinstance(p.get("name"), str)
    ]
    valid_kw = [str(kw).lower() for kw in shared_kw if isinstance(kw, str)]
    valid_ex_kw = [str(ex).lower() for ex in shared_ex_kw if isinstance(ex, str)]
    filtered = [
        n
        for n in all_names
        if any(kw in n.lower() for kw in valid_kw)
        and not any(ex in n.lower() for ex in valid_ex_kw)
    ]
    return filtered, all_names


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
    up_pref: str,
    down_pref: str,
    shared_kw: list,
    shared_ex_kw: list,
    clean_node_fn,
):
    try:
        input_data = yaml.safe_load(remote_yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse remote YAML: {e}")

    if not isinstance(input_data, dict) or not input_data.get("proxies"):
        preview = remote_yaml_text[:100].replace("\n", " ") if remote_yaml_text else "Empty content"
        raise ValueError(f"No valid proxies found in remote YAML. Preview: {preview}")

    with open(template_path, "r", encoding="utf-8") as f:
        template_data = yaml.safe_load(f)
        
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
    shared_kw,
    shared_ex_kw,
    clean_fn,
    custom_node_path,
    target_groups,
    inject_templates,
    base_dir,
):
    clash_config_val = None
    
    if "clash_tun" in ua or "ClashMetaForAndroid" in ua:
        clash_config_val = "tun"
    elif any(k in ua for k in ["clash_pc", "clash_m", "clash_openwrt"]) or "clash" in ua.lower():
        clash_config_val = "standard"
    else:
        abort(404)

    config_map = {
        "standard": (base_dir / "yaml/config.yaml", "50 Mbps", "100 Mbps"),
        "tun": (base_dir / "yaml/config_tun.yaml", "50 Mbps", "100 Mbps"),
    }
    template_path, up, down = config_map[clash_config_val]

    try:
        # Extract dynamic header from fetch_remote_yaml
        remote_yaml_text, userinfo_header = fetch_remote_yaml(
            unquote(url), source, is_force_refresh, cache_dir, cache_expire
        )
        
        output_bytes = process_yaml_content_clash(
            remote_yaml_text, template_path, up, down, shared_kw, shared_ex_kw, clean_fn
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


# ================= Routing & Dispatch =================
@app.before_request
def restrict_paths():
    # Only allow WAF whitelisted paths
    if request.path not in {"/mitce", "/bajie"}:
        abort(404)
    if not (key := request.args.get("key")):
        abort(404)
    if not hmac.compare_digest(
        hashlib.sha256(key.encode("utf-8")).hexdigest(), ACCESS_KEY_SHA256
    ):
        abort(404)


@app.route("/<source>")
def process_source(source):
    # Dynamically read from ACTUAL_SOURCE file instead of SOURCE_MAP
    actual_source = ACTUAL_SOURCE
    path = BASE_DIR / actual_source
    
    if not path.is_file():
        abort(404)

    ua = request.headers.get("User-Agent", "")
    is_force_refresh = "u" in request.args

    try:
        url = read_url_from_file(path)
    except Exception as e:
        return str(e), 500

    if "Clash" in ua or "clash" in ua.lower():
        return handle_request(
            actual_source,
            url,
            ua,
            is_force_refresh,
            CACHE_DIR,
            CACHE_EXPIRE_SECONDS,
            SHARED_KEYWORDS,
            SHARED_EXCLUDE_KEYWORDS,
            clean_node_name,
            CUSTOM_CLASH_NODE,
            TARGET_GROUPS,
            INJECT_TEMPLATES,
            BASE_DIR,
        )

    abort(404)


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")