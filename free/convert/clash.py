import json
import logging
import os
import re
import time
from pathlib import Path
import requests
import yaml

logger = logging.getLogger(__name__)

# ================= [Clash] 专用配置 =================
CLASH_TEMPLATE_PC = Path("yaml/pc.yaml")
CLASH_TEMPLATE_MTUN = Path("yaml/mtun.yaml")
CLASH_TEMPLATE_OPENWRT = Path("yaml/openwrt.yaml")
CLASH_TEMPLATE_M = Path("yaml/m.yaml")

CLASH_USER_AGENT = "clash-verge"
CLASH_INCLUDED_HEADERS = ["Subscription-Userinfo"]
CLASH_HY2_UP = "50 Mbps"
CLASH_HY2_DOWN = "100 Mbps"
CLASH_HY2_UP_M = "30 Mbps"
CLASH_HY2_DOWN_M = "60 Mbps"
CLASH_FINGERPRINT = "firefox"


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
            logger.warning(f"读取缓存属性失败，将尝试网络请求: {e}")

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
    all_names = [p.get("name") for p in proxies if isinstance(p, dict) and "name" in p]
    filtered = [
        n
        for n in all_names
        if any(kw.lower() in n.lower() for kw in shared_kw)
        and not any(ex.lower() in n.lower() for ex in shared_ex_kw)
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
                        logger.error(f"分组 {group.get('name')} 正则错误: {e}")

                    if group.get("proxies"):
                        temp_groups.append(group)
                else:
                    temp_groups.append(group)

            final_groups = []
            surviving_group_names = {g["name"] for g in temp_groups if "name" in g}
            BUILT_IN = {"DIRECT", "REJECT", "no-resolve", "PASS"}
            valid_targets = set(all_node_names) | surviving_group_names | BUILT_IN

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
        logger.error(f"解析YAML内容失败: {e}")
        raise
