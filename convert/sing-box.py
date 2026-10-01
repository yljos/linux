import json
import logging
import re
from pathlib import Path

import yaml
from flask import Response, jsonify

logger = logging.getLogger(__name__)


# ================= Protocol Converters =================
def clash_to_singbox_node(c_node: dict) -> dict:
    if not isinstance(c_node, dict):
        return None

    c_type = c_node.get("type", "").lower()
    sb_node = {
        "tag": c_node.get("name", "Unknown"),
        "server": c_node.get("server"),
        "server_port": c_node.get("port", 443),
    }

    if c_type == "vless":
        sb_node["type"] = "vless"
        sb_node["uuid"] = c_node.get("uuid")
        if c_node.get("flow"):
            sb_node["flow"] = c_node.get("flow")

        # TLS config mapping
        if c_node.get("tls", False):
            sb_node["tls"] = {
                "enabled": True,
                "server_name": c_node.get(
                    "sni", c_node.get("servername", sb_node["server"])
                ),
                "insecure": c_node.get("skip-cert-verify", False),
            }
            # Reality opts mapping
            ropts = c_node.get("reality-opts", {})
            if ropts:
                sb_node["tls"]["reality"] = {
                    "enabled": True,
                    "public_key": ropts.get("public-key", ""),
                    "short_id": ropts.get("short-id", ""),
                }

        # Transport mapping
        network = c_node.get("network", "tcp")
        if network == "ws":
            ws_opts = c_node.get("ws-opts", {})
            sb_node["transport"] = {
                "type": "ws",
                "path": ws_opts.get("path", "/"),
                "headers": ws_opts.get("headers", {}),
            }
        elif network == "grpc":
            grpc_opts = c_node.get("grpc-opts", {})
            sb_node["transport"] = {
                "type": "grpc",
                "service_name": grpc_opts.get("grpc-service-name", ""),
            }

    elif c_type in ["hysteria2", "hy2"]:
        sb_node["type"] = "hysteria2"
        sb_node["password"] = str(c_node.get("password", ""))
        sb_node["up_mbps"] = 50
        sb_node["down_mbps"] = 200

        # Handle port range for hy2
        if "ports" in c_node:
            sb_node["server_ports"] = str(c_node["ports"]).replace("-", ":")
            if "server_port" in sb_node:
                del sb_node["server_port"]

        sb_node["tls"] = {
            "enabled": True,
            "server_name": c_node.get("sni", sb_node["server"]),
            "insecure": c_node.get("skip-cert-verify", False),
        }

        if c_node.get("obfs"):
            sb_node["obfs"] = {
                "type": c_node.get("obfs"),
                "password": c_node.get("obfs-password", ""),
            }
    elif c_type == "trojan":
        sb_node["type"] = "trojan"
        sb_node["password"] = str(c_node.get("password", ""))

        tls = {"enabled": True}
        if "sni" in c_node:
            tls["server_name"] = c_node["sni"]
        if c_node.get("skip-cert-verify"):
            tls["insecure"] = True

        sb_node["tls"] = tls

        if c_node.get("network") == "ws":
            sb_node["transport"] = {
                "type": "ws",
                "path": c_node.get("ws-opts", {}).get("path", "/"),
            }
    elif c_type in ["ss", "shadowsocks"]:
        sb_node["type"] = "shadowsocks"
        sb_node["method"] = c_node.get("cipher")
        sb_node["password"] = str(c_node.get("password", ""))

    else:
        # Skip unsupported protocols strictly
        return None

    return sb_node


# ================= Main Processor =================
def fetch_and_process_singbox(
    yaml_path: Path,
    template_path: str,
    mixin_paths: list,
    shared_kw: list,
    shared_ex_kw: list,
    clean_node_fn,
):
    # Read local Clash YAML
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Read YAML Error: {e}")

    # Extract Clash proxies
    raw_nodes = []
    if isinstance(yaml_data, dict):
        raw_nodes = yaml_data.get("proxies", [])
    elif isinstance(yaml_data, list):
        raw_nodes = yaml_data

    # Convert to Sing-box formats
    nodes = []
    for c_node in raw_nodes:
        original_name = c_node.get("name", "")
        # Remote node filtering logic is preserved here
        if not original_name or any(ex in original_name for ex in shared_ex_kw):
            continue

        # Perform exact protocol conversion
        sb_node = clash_to_singbox_node(c_node)
        if not sb_node:
            continue

        sb_node["tag"] = clean_node_fn(original_name)
        nodes.append(sb_node)

    if not nodes:
        raise ValueError("No valid nodes converted from local YAML")

    # Load base config
    with open(template_path, "r", encoding="utf-8") as f:
        base_config = json.load(f)

    # Merge mixin configurations
    for m_path in mixin_paths:
        path_obj = Path(m_path)
        if path_obj.exists():
            with open(path_obj, "r", encoding="utf-8") as f:
                m_data = json.load(f)
                if isinstance(m_data, dict):
                    base_config.update(m_data)

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
        # Read custom Sing-box nodes
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
):
    mixin_paths = []
    template_path = "json/config.json"

    ua_lower = ua.lower()

    # Determine routing and add specific mixin files
    if any(k in ua_lower for k in ["sfa", "sing-box_tun"]):
        mixin_paths.append("json/tun.json")
    elif "openwrt" in ua_lower:
        mixin_paths.append("json/tproxy.json")
    else:
        pass  # Standard, no mixins

    # Strictly read local cache file only
    yaml_path = cache_dir / f"{source}.yaml"
    if not yaml_path.exists():
        return (
            jsonify(
                {
                    "error": f"Local YAML cache not found: {yaml_path}. Please fetch via Clash first."
                }
            ),
            404,
        )

    try:
        json_str = fetch_and_process_singbox(
            yaml_path,
            template_path,
            mixin_paths,
            shared_kw,
            shared_ex_kw,
            clean_fn,
        )

        # Unconditionally inject custom local nodes
        json_str = inject_custom_singbox_node(json_str, custom_node_path, target_groups)

        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=config.json"},
        )
    except Exception as e:
        logger.error(f"Singbox Error: {e}")
        return jsonify({"error": str(e)}), 500
