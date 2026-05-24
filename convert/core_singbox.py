import json
import logging
import os
import re
import time
from pathlib import Path
import requests
import yaml

from config import SB_TEMPLATE_MAP
from parsers import clash_to_singbox

logger = logging.getLogger(__name__)

def fetch_and_process_singbox(source: str, config_param: str, force_refresh: bool, url: str, cache_dir: Path, cache_expire: int, shared_kw: list, shared_ex_kw: list, clean_node_fn):
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

    if force_refresh: logger.info(f"[{source}] [Sing-Box] [Received u]")

    if not used_cache:
        try:
            headers = {"User-Agent": "clash-verge"}
            logger.info(f"[{source}] [Sing-Box] [Fetching ...]")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            temp_content = response.text.strip()
            if "proxies:" not in temp_content: raise ValueError("[Invalid Clash YAML Content]")
            
            yaml_content = temp_content
            with open(cache_file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            logger.info(f"[{source}] [Sing-Box] [Updated Successfully]")
        except Exception as e:
            logger.error(f"[{source}] [Sing-Box] [Error] [Loaded cache] {e}")
            if cache_file_path.exists():
                logger.warning(f"[{source}] [Sing-Box] Fallback to expired cache")
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    yaml_content = f.read()
            else:
                raise RuntimeError(f"[{source}] [Fetch Error]")

    try:
        clash_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as ye:
        raise ValueError(f"YAML parsing failed: {str(ye)}")

    if not isinstance(clash_data, dict) or "proxies" not in clash_data:
        raise ValueError("Invalid Clash configuration")

    raw_proxies = clash_data["proxies"]
    nodes = []
    for proxy in raw_proxies:
        try:
            original_name = proxy.get("name", "")
            if any(ex in original_name for ex in shared_ex_kw): continue
            proxy["name"] = clean_node_fn(original_name)
            sb_node = clash_to_singbox(proxy)
            if sb_node: nodes.append(sb_node)
        except Exception:
            continue

    if not nodes: raise ValueError("No nodes converted successfully")

    template_filename = SB_TEMPLATE_MAP.get(config_param, SB_TEMPLATE_MAP["openwrt"])
    if not os.path.exists(template_filename): raise FileNotFoundError(f"Template file not found: {template_filename}")

    with open(template_filename, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    outbounds = base_config.get("outbounds", [])
    existing_tags = {o.get("tag") for o in outbounds}
    new_nodes = [n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags]
    outbounds.extend(new_nodes)

    def node_tag_valid(tag: str) -> bool:
        tag_upper = tag.upper() if tag else ""
        if not any(region.upper() in tag_upper for region in shared_kw): return False
        if any(exclude.upper() in tag_upper for exclude in shared_ex_kw): return False
        return True

    filtered_outbounds = [
        o for o in outbounds
        if node_tag_valid(o.get("tag", "")) or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]
    ]

    temp_outbounds = []
    all_node_tags = [o.get("tag") for o in filtered_outbounds if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]]

    # Core fix area: Refactored merge logic for policy groups and regex matching
    for outbound in filtered_outbounds:
        if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
            filters = outbound.pop("filter", [])
            regex_list = [reg for f in filters if isinstance(f, dict) for reg in f.get("regex", [])]
            original_outbounds = outbound.get("outbounds", [])
            if "{all}" in original_outbounds: original_outbounds.remove("{all}")

            if not regex_list:
                if original_outbounds:
                    outbound["outbounds"] = list(dict.fromkeys(original_outbounds))
                    temp_outbounds.append(outbound)
                continue

            pattern = "|".join(regex_list)
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                matched_tags = [tag for tag in all_node_tags if compiled.search(tag)]
                merged_outbounds = list(dict.fromkeys(original_outbounds + matched_tags))
                if merged_outbounds:
                    outbound["outbounds"] = merged_outbounds
                    temp_outbounds.append(outbound)
            except re.error as e:
                logger.error(f"Invalid regular expression: {e}")
                if original_outbounds:
                    outbound["outbounds"] = list(dict.fromkeys(original_outbounds))
                    temp_outbounds.append(outbound)
        else:
            temp_outbounds.append(outbound)

    final_outbounds = []
    surviving_tags = {o.get("tag") for o in temp_outbounds if o.get("tag")}

    for outbound in temp_outbounds:
        if "outbounds" in outbound and isinstance(outbound["outbounds"], list):
            original_refs = outbound["outbounds"]
            cleaned_refs = [tag for tag in original_refs if tag in surviving_tags]
            outbound["outbounds"] = cleaned_refs
            if not cleaned_refs: continue
        final_outbounds.append(outbound)

    for outbound in final_outbounds:
        if outbound.get("type") == "selector":
            current_outbounds = outbound.get("outbounds", [])
            current_default = outbound.get("default", "")
            if current_outbounds and current_default not in current_outbounds:
                outbound["default"] = current_outbounds[0]

    base_config["outbounds"] = final_outbounds
    return json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))