import hashlib
import hmac
import io
import json
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import unquote
from typing import Any, Dict, List, Tuple

import requests
import yaml
try:
    from yaml import CSafeLoader as Loader, CSafeDumper as Dumper
except ImportError:
    from yaml import SafeLoader as Loader, SafeDumper as Dumper
from flask import Flask, send_file, request, abort

# ================= Logging =================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ================= Auth & General Config =================
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

SOURCE_MAP = {
    "mitce": BASE_DIR / "mitce",
    "bajie": BASE_DIR / "bajie",
}

# ================= Custom Node Config =================
CUSTOM_CLASH_NODE = BASE_DIR / "node.yaml"
TARGET_GROUPS = ["Google"]
INJECT_TEMPLATES = ["m", "openwrt"]

# ================= Keywords & Rename Maps =================
RENAME_MAP = {
    "香港": "HK",
    "美国": "US",
    "新加坡": "SG",
    "日本": "JP",
    "家宽": "ISP",
}

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

# ================= Config =================
CLASH_TEMPLATE_PC = BASE_DIR / "yaml/pc.yaml"
CLASH_TEMPLATE_MTUN = BASE_DIR / "yaml/mtun.yaml"
CLASH_TEMPLATE_OPENWRT = BASE_DIR / "yaml/openwrt.yaml"
CLASH_TEMPLATE_M = BASE_DIR / "yaml/m.yaml"

CLASH_USER_AGENT = "clash-verge"
CLASH_INCLUDED_HEADERS = ["Subscription-Userinfo"]
CLASH_HY2_UP = "50 Mbps"
CLASH_HY2_DOWN = "200 Mbps"
CLASH_HY2_UP_M = "30 Mbps"
CLASH_HY2_DOWN_M = "60 Mbps"
CLASH_FINGERPRINT = "firefox"


# ================= Utils =================
def read_url_from_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                return url
    raise ValueError(f"URL [None]: {path}")


def clean_node_name(name: str) -> str:
    if not name:
        return name
    for k, v in RENAME_MAP.items():
        name = name.replace(k, v)
    name = re.sub(r"[^\x00-\x7F]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def inject_custom_clash_node(
    yaml_bytes: bytes, node_path: Path, target_groups: list
) -> bytes:
    if not node_path.exists():
        return yaml_bytes
    try:
        with open(node_path, "r", encoding="utf-8") as f:
            custom_data = yaml.load(f, Loader=Loader)
        if not custom_data:
            return yaml_bytes

        nodes = custom_data if isinstance(custom_data, list) else [custom_data]
        config = yaml.load(yaml_bytes, Loader=Loader)

        for node in nodes:
            if not isinstance(node, dict) or "name" not in node:
                continue
            config.setdefault("proxies", []).append(node)

        return yaml.dump(config, Dumper=Dumper, allow_unicode=True, sort_keys=False).encode(
            "utf-8"
        )
    except Exception as e:
        logger.error(f"Node injection failed: {e}")
        return yaml_bytes


def save_headers_to_disk(source_name: str, headers: dict, cache_dir: Path) -> dict:
    try:
        filtered = {
            k: v
            for k, v in headers.items()
            if k.lower() in {h.lower() for h in CLASH_INCLUDED_HEADERS}
        }
        if not filtered:
            return {}
        file_path = cache_dir / f"{source_name}.headers.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        return filtered
    except Exception as e:
        logger.error(f"Save headers error: {e}")
        return {}


def load_headers_from_disk(source_name: str, cache_dir: Path) -> dict:
    file_path = cache_dir / f"{source_name}.headers.json"
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ================= Parsers =================
def is_valid_clash_yaml(text: str) -> bool:
    return bool(text and "proxies:" in text)


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
        up_v = up_pref if "bps" in up_pref.lower() else f"{up_pref} Mbps"
        down_v = down_pref if "bps" in down_pref.lower() else f"{down_pref} Mbps"
        proxy.update({"up": up_v, "down": down_v, "skip-cert-verify": False})
    elif p_type == "vless":
        proxy.update({"skip-cert-verify": False, "packet-encoding": "xudp"})
        if "client-fingerprint" in proxy:
            proxy["client-fingerprint"] = CLASH_FINGERPRINT


# ================= Core Logic =================
def fetch_yaml_text_clash(
    url: str, source_name: str, force_refresh: bool, cache_dir: Path, cache_expire: int
):
    yaml_cache_file = cache_dir / f"{source_name}.yaml"
    if not force_refresh and yaml_cache_file.exists():
        try:
            mtime = os.path.getmtime(yaml_cache_file)
            if time.time() - mtime < cache_expire:
                logger.info(f"[{source_name}] Cache loaded")
                with open(yaml_cache_file, "r", encoding="utf-8") as f:
                    return f.read(), load_headers_from_disk(source_name, cache_dir)
        except Exception as e:
            logger.warning(f"Cache attributes read failed: {e}")

    if force_refresh:
        logger.info(f"[{source_name}] Force refresh requested")

    try:
        headers = {"User-Agent": CLASH_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        text_content = response.text.lstrip("\ufeff").replace("\r\n", "\n")

        if is_valid_clash_yaml(text_content):
            save_headers_to_disk(source_name, response.headers, cache_dir)
            with open(yaml_cache_file, "w", encoding="utf-8") as f:
                f.write(text_content)
            logger.info(f"[{source_name}] Updated successfully")
            return text_content, response.headers
        else:
            logger.warning(f"[{source_name}] Fetch error, fallback to cache")
    except Exception as e:
        logger.error(f"[{source_name}] Update error: {e}")

    if yaml_cache_file.exists():
        logger.info(f"[{source_name}] Cache loaded (fallback)")
        with open(yaml_cache_file, "r", encoding="utf-8") as f:
            return f.read(), load_headers_from_disk(source_name, cache_dir)

    raise RuntimeError(f"[{source_name}] Error")


def process_yaml_content_clash(
    yaml_text: str,
    template_path: Path,
    up_pref: str,
    down_pref: str,
    shared_kw: list,
    shared_ex_kw: list,
    clean_node_fn,
):
    try:
        input_data = yaml.load(yaml_text, Loader=Loader)
        if not isinstance(input_data, dict):
            raise ValueError("[Invalid YAML Format]")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.load(f, Loader=Loader)

        proxies_orig = input_data.get("proxies", [])
        filtered_names, _ = filter_node_names_clash(
            proxies_orig, shared_kw, shared_ex_kw
        )

        final_proxies = []
        for p in proxies_orig:
            if isinstance(p, dict) and p.get("name") in filtered_names:
                p["name"] = clean_node_fn(p["name"])
                process_proxy_config_clash(p, up_pref, down_pref)
                final_proxies.append(p)

        # Overwrite file with literal string if no nodes matched
        if not final_proxies:
            return b"NO_NODES"

        final_proxies.append({"name": "dns-out", "type": "dns"})
        template_data["proxies"] = final_proxies

        if "proxy-groups" in template_data:
            raw_groups = template_data["proxy-groups"]
            all_node_names = [p["name"] for p in final_proxies]
            temp_groups = []

            for group in raw_groups:
                if "filter" in group:
                    existing_proxies = group.get("proxies", [])
                    pattern = group.pop("filter")
                    group.pop("include-all-proxies", None)
                    try:
                        matcher = re.compile(pattern, re.IGNORECASE)
                        matched_names = [n for n in all_node_names if matcher.search(n)]
                        group["proxies"] = existing_proxies + [
                            n for n in matched_names if n not in existing_proxies
                        ]
                    except Exception as e:
                        logger.error(f"Group {group.get('name')} regex error: {e}")
                    if group.get("proxies"):
                        temp_groups.append(group)
                else:
                    temp_groups.append(group)

            final_groups = []
            surviving_group_names = {g["name"] for g in temp_groups if "name" in g}
            built_in = {"DIRECT", "REJECT", "PASS", "REJECT-DROP", "GCP-outbound"}
            valid_targets = set(all_node_names) | surviving_group_names | built_in

            for group in temp_groups:
                original_refs = group.get("proxies", [])
                if not original_refs:
                    continue
                cleaned_refs = [ref for ref in original_refs if ref in valid_targets]
                if cleaned_refs:
                    group["proxies"] = cleaned_refs
                    final_groups.append(group)
            template_data["proxy-groups"] = final_groups

        output = yaml.dump(
            template_data,
            Dumper=Dumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=4096,
        )
        return output.encode("utf-8")
    except Exception as e:
        logger.error(f"Failed to parse YAML content: {e}")
        raise


# ================= Flask App & Routes =================
app = Flask(__name__)


@app.before_request
def restrict_paths():
    if request.path not in {"/mitce", "/bajie"}:
        abort(404)
    key = request.args.get("key")
    if not key:
        abort(404)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(digest, ACCESS_KEY_SHA256):
        abort(404)


@app.route("/<source>")
def process_source(source):
    path = SOURCE_MAP.get(source)
    if not path:
        abort(404)

    ua = request.headers.get("User-Agent", "")
    is_force_refresh = "u" in request.args

    clash_config_val = None
    if "ClashMetaForAndroid" in ua:
        clash_config_val = "mtun"
    elif "clash_pc" in ua:
        clash_config_val = "pc"
    elif "clash_openwrt" in ua:
        clash_config_val = "openwrt"
    elif "clash_m" in ua:
        clash_config_val = "m"

    if clash_config_val:
        config_map = {
            "m": (CLASH_TEMPLATE_M, CLASH_HY2_UP_M, CLASH_HY2_DOWN_M),
            "mtun": (CLASH_TEMPLATE_MTUN, CLASH_HY2_UP_M, CLASH_HY2_DOWN_M),
            "pc": (CLASH_TEMPLATE_PC, CLASH_HY2_UP, CLASH_HY2_DOWN),
            "openwrt": (CLASH_TEMPLATE_OPENWRT, CLASH_HY2_UP, CLASH_HY2_DOWN),
        }
        template_path, up, down = config_map[clash_config_val]
        logger.info(f"[{source}] Tpl:{clash_config_val} Force:{is_force_refresh} UA:{ua}")

        try:
            url = read_url_from_file(path)
            yaml_text, headers_data = fetch_yaml_text_clash(
                unquote(url),
                source,
                is_force_refresh,
                CACHE_DIR,
                CACHE_EXPIRE_SECONDS,
            )
            output_bytes = process_yaml_content_clash(
                yaml_text,
                template_path,
                up,
                down,
                SHARED_KEYWORDS,
                SHARED_EXCLUDE_KEYWORDS,
                clean_node_name,
            )

            # Prevent YAML exception when output_bytes is literal NO_NODES
            if output_bytes != b"NO_NODES" and clash_config_val in INJECT_TEMPLATES:
                output_bytes = inject_custom_clash_node(
                    output_bytes, CUSTOM_CLASH_NODE, TARGET_GROUPS
                )

            if output_bytes == b"NO_NODES":
                logger.warning(f"[{source}] Node empty, generating NO_NODES file")

            response = send_file(
                io.BytesIO(output_bytes),
                mimetype="text/yaml",
                as_attachment=True,
                download_name="config.yaml",
            )
            if headers_data:
                for h, v in headers_data.items():
                    if h.lower() in {ih.lower() for ih in CLASH_INCLUDED_HEADERS}:
                        response.headers[h] = v
            return response
        except Exception as e:
            logger.error(f"Error: {e}")
            return str(e), 500

    abort(404)


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")