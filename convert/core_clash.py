import logging
import os
import re
import time
from pathlib import Path
import requests
import yaml

from config import CLASH_USER_AGENT
from utils import save_headers_to_disk, load_headers_from_disk
from parsers import (
    is_valid_clash_yaml,
    filter_node_names_clash,
    process_proxy_config_clash,
)

logger = logging.getLogger(__name__)


def fetch_yaml_text_clash(
    url: str, source_name: str, force_refresh: bool, cache_dir: Path, cache_expire: int
):
    yaml_cache_file = cache_dir / f"{source_name}.yaml"
    if not force_refresh and yaml_cache_file.exists():
        try:
            mtime = os.path.getmtime(yaml_cache_file)
            if time.time() - mtime < cache_expire:
                logger.info(f"[{source_name}] [Clash] [Loaded cache]")
                with open(yaml_cache_file, "r", encoding="utf-8") as f:
                    return f.read(), load_headers_from_disk(source_name, cache_dir)
        except Exception as e:
            logger.warning(
                f"Failed to read cache attributes, attempting network request: {e}"
            )

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
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=4096,
        )
        return output.encode("utf-8")
    except Exception as e:
        logger.error(f"Failed to parse YAML content: {e}")
        raise
