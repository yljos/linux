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

import requests
import yaml
from flask import Flask, send_file, request, abort

app = Flask(__name__)

# ================= Auth and General Config =================
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"

# Get the absolute path of the current script directory
BASE_DIR = Path(__file__).resolve().parent

CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

source_map = {
    "mitce": BASE_DIR / "mitce",
    "bajie": BASE_DIR / "bajie",
}

# Custom node file path
CUSTOM_CLASH_NODE = BASE_DIR / "node.yaml"

# Target groups to inject custom nodes
TARGET_GROUPS = ["Google"]

# Client templates to inject custom nodes
INJECT_TEMPLATES = ["m", "openwrt"]

# ================= Clash Specific Config =================
CLASH_TEMPLATE_PC = BASE_DIR / "yaml" / "pc.yaml"
CLASH_TEMPLATE_MTUN = BASE_DIR / "yaml" / "mtun.yaml"
CLASH_TEMPLATE_OPENWRT = BASE_DIR / "yaml" / "openwrt.yaml"
CLASH_TEMPLATE_M = BASE_DIR / "yaml" / "m.yaml"

CLASH_USER_AGENT = "clash-verge"
CLASH_INCLUDED_HEADERS = ["Subscription-Userinfo"]
CLASH_HY2_UP = "50 Mbps"
CLASH_HY2_DOWN = "200 Mbps"
CLASH_HY2_UP_M = "30 Mbps"
CLASH_HY2_DOWN_M = "60 Mbps"
CLASH_FINGERPRINT = "firefox"

# ================= Keywords and Blacklist =================
RENAME_MAP = {
    "香港": "HK",
    "美国": "US",
    "新加坡": "SG",
    "日本": "JP",
    "家宽": "ISP",
}

SHARED_KEYWORDS = [
    "US", "HK", "SG", "JP", "Hong Kong", "Singapore", "Japan", "United States", 
    "美国", "香港", "新加坡", "日本",
]

SHARED_EXCLUDE_KEYWORDS = [
    "官网", "流量", "倍率", "剩余", "Australia", "到期", "重置", 
    "HK2-HY2", "HK3-HY2", "HK4-HY2", "HK5-HY2",
]

# ================= Logging and Utilities =================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


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


# ================= Clash Processing Functions =================
def is_valid_clash_yaml(text: str) -> bool:
    if not text:
        return False
    return "proxies:" in text


def save_headers_to_disk(source_name, headers, cache_dir):
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
        logger.error(f"save Headers Error: {e}")
        return {}


def load_headers_from_disk(source_name, cache_dir):
    file_path = cache_dir / f"{source_name}.headers.json"
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_yaml_text_clash(url, source_name, force_refresh, cache_dir, cache_expire):
    yaml_cache_file = cache_dir / f"{source_name}.yaml"

    if not force_refresh and yaml_cache_file.exists():
        try:
            mtime = os.path.getmtime(yaml_cache_file)
            if time.time() - mtime < cache_expire:
                logger.info(f"[{source_name}] [Clash] [Loaded cache]")
                with open(yaml_cache_file, "r", encoding="utf-8") as f:
                    return f.read(), load_headers_from_disk(source_name, cache_dir)
        except Exception as e:
            logger.warning(f"Failed to read cache attributes, will try network request: {e}")

    if force_refresh:
        logger.info(f"[{source_name}] [Clash] [Received u]")

    try:
        headers = {"User-Agent": CLASH_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        text_content = response.text.lstrip("\ufeff").replace("\r\n", "\n")

        if is_valid_clash_yaml(text_content):
            save_headers_to_disk(source_name, response.headers, cache_dir)
            with open(yaml_cache_file, "w", encoding="utf-8") as f:
                f.write(text_content)
            logger.info(f"[{source_name}] [Clash Updated Successfully]")
            return text_content, response.headers
        else:
            logger.warning(f"[{source_name}] [Clash] [Fetch Error] [Fallback To Cache]")
    except Exception as e:
        logger.error(f"[{source_name}] [Clash] [Updated Error]: {e}")

    if yaml_cache_file.exists():
        logger.info(f"[{source_name}] [Clash] [Loaded cache] [Fallback]")
        with open(yaml_cache_file, "r", encoding="utf-8") as f:
            return f.read(), load_headers_from_disk(source_name, cache_dir)

    raise RuntimeError(f"[{source_name}] [Error]")


def filter_node_names_clash(proxies, shared_kw, shared_ex_kw):
    all_names = [
        str(p.get("name"))  # Explicitly declare as str to eliminate editor type warnings
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


def process_proxy_config_clash(proxy, up_pref, down_pref):
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


def process_yaml_content_clash(
    yaml_text: str,
    template_path: Path,
    up_pref: str,
    down_pref: str,
    shared_kw,
    shared_ex_kw,
    clean_node_fn,
):
    try:
        input_data = yaml.safe_load(yaml_text)
        if not isinstance(input_data, dict):
            raise ValueError("[Invalid YAML Format]")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.safe_load(f)

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

        if not final_proxies and proxies_orig:
            logger.warning("[Node None] [Fallback To All Nodes]")
            for p in proxies_orig:
                if isinstance(p, dict):
                    p["name"] = clean_node_fn(p.get("name", ""))
                    process_proxy_config_clash(p, up_pref, down_pref)
            final_proxies = proxies_orig

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

                        combined = existing_proxies + [
                            n for n in matched_names if n not in existing_proxies
                        ]
                        group["proxies"] = combined

                    except Exception as e:
                        logger.error(f"Regex error for group {group.get('name')}: {e}")

                    if group.get("proxies"):
                        temp_groups.append(group)
                else:
                    temp_groups.append(group)

            final_groups = []
            surviving_group_names = {g["name"] for g in temp_groups if "name" in g}
            built_in = {"DIRECT", "REJECT", "PASS"}
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
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=4096,
        )
        return output.encode("utf-8")
    except Exception as e:
        logger.error(f"Failed to parse YAML content: {e}")
        raise


def inject_custom_clash_node(
    yaml_bytes: bytes, node_path: Path, target_groups: list
) -> bytes:
    """Inject custom Clash nodes and add to specified proxy groups"""
    if not node_path.exists():
        return yaml_bytes

    try:
        with open(node_path, "r", encoding="utf-8") as f:
            custom_data = yaml.safe_load(f)

        if not custom_data:
            return yaml_bytes

        # 统一转换为列表处理
        nodes = custom_data if isinstance(custom_data, list) else [custom_data]
        config = yaml.safe_load(yaml_bytes)
        
        # 确保基础结构存在，防止极端情况报错
        if "proxies" not in config:
            config["proxies"] = []
        if "proxy-groups" not in config:
            config["proxy-groups"] = []

        for node in nodes:
            if not isinstance(node, dict) or "name" not in node:
                continue

            node_name = node["name"]

            # 1. 将自定义节点追加到所有代理的列表里
            config["proxies"].append(node)

            # 2. 尝试追加到指定的策略组
            for target in target_groups:
                group_found = False
                for group in config["proxy-groups"]:
                    if group.get("name") == target:
                        group_found = True
                        # 避免节点重复插入
                        if node_name not in group.setdefault("proxies", []):
                            group["proxies"].append(node_name)
                        break
                
                # 核心修复 1：如果目标策略组在前面的清洗中因为“空节点”被删除了，我们需要把它重新建出来
                if not group_found:
                    config["proxy-groups"].append({
                        "name": target,
                        "type": "select",  # 默认重建为 select 类型
                        "proxies": [node_name]
                    })

        # 核心修复 2：加上 default_flow_style=False 和 width=4096，保证输出严格、标准的多行 YAML 格式
        return yaml.dump(
            config, 
            allow_unicode=True, 
            sort_keys=False, 
            default_flow_style=False, 
            width=4096
        ).encode("utf-8")
        
    except Exception as e:
        logger.error(f"[Clash] Failed to merge custom node: {e}")
        return yaml_bytes


# ================= Routing and Distribution =================
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
    path = source_map.get(source)
    if not path:
        abort(404)

    ua = request.headers.get("User-Agent", "")
    is_force_refresh = "u" in request.args

    # --- Clash Distribution Logic ---
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
            "m": (
                CLASH_TEMPLATE_M,
                CLASH_HY2_UP_M,
                CLASH_HY2_DOWN_M,
            ),
            "mtun": (
                CLASH_TEMPLATE_MTUN,
                CLASH_HY2_UP_M,
                CLASH_HY2_DOWN_M,
            ),
            "pc": (
                CLASH_TEMPLATE_PC,
                CLASH_HY2_UP,
                CLASH_HY2_DOWN,
            ),
            "openwrt": (
                CLASH_TEMPLATE_OPENWRT,
                CLASH_HY2_UP,
                CLASH_HY2_DOWN,
            ),
        }

        template_path, up, down = config_map[clash_config_val]
        logger.info(
            f"[Clash] | [Template: {clash_config_val}] | [Force: {is_force_refresh}] | [UA: {ua}]"
        )

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

            # Inject nodes only in specified templates
            if clash_config_val in INJECT_TEMPLATES:
                output_bytes = inject_custom_clash_node(
                    output_bytes, CUSTOM_CLASH_NODE, TARGET_GROUPS
                )

            response = send_file(
                io.BytesIO(output_bytes),
                mimetype="text/yaml",
                as_attachment=True,
                download_name="config.yaml",
            )
            if headers_data:
                for h, v in headers_data.items():
                    if h.lower() in {
                        ih.lower() for ih in CLASH_INCLUDED_HEADERS
                    }:
                        response.headers[h] = v
            return response
        except Exception as e:
            logger.error(f"Clash [Error]: {e}")
            return str(e), 500

    abort(404)


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")