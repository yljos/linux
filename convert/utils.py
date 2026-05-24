import json
import logging
import re
from pathlib import Path
import yaml
from config import RENAME_MAP, CLASH_INCLUDED_HEADERS

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


def inject_custom_clash_node(
    yaml_bytes: bytes, node_path: Path, target_groups: list
) -> bytes:
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
            if not isinstance(node, dict) or "name" not in node:
                continue
            config.setdefault("proxies", []).append(node)

        return yaml.safe_dump(config, allow_unicode=True, sort_keys=False).encode(
            "utf-8"
        )
    except Exception as e:
        logger.error(f"[Clash] Custom node injection failed: {e}")
        return yaml_bytes


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
            if not isinstance(outbound, dict) or "tag" not in outbound:
                continue
            node_tag = outbound["tag"]
            config.setdefault("outbounds", []).append(outbound)

            for cfg_outbound in config.get("outbounds", []):
                if cfg_outbound.get("tag") in target_groups and cfg_outbound.get(
                    "type"
                ) in ["selector", "urltest"]:
                    cfg_outbound.setdefault("outbounds", []).append(node_tag)

        return json.dumps(config, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[Sing-box] Custom node injection failed: {e}")
        return json_str


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
