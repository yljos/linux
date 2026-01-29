import re
import os
import io
import json
import yaml
import hashlib
import hmac
import logging
import requests
import time
from pathlib import Path
from urllib.parse import unquote
from typing import Any, Dict, Union
from flask import Flask, send_file, request, abort, Response, jsonify

app = Flask(__name__)

# ================= 鉴权与通用配置 =================

ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# [配置] 缓存过期时间 (单位: 秒)
# 86400秒 = 24小时。
# 如果想强制刷新，请在 URL 后加 &u
CACHE_EXPIRE_SECONDS = 86400

MITCE_URL_FILE = Path("mitce").absolute()
BAJIE_URL_FILE = Path("bajie").absolute()
source_map = {
    "mitce": MITCE_URL_FILE,
    "bajie": BAJIE_URL_FILE,
}

# ================= [合并] 关键词与黑名单 =================

# 1. 节点重命名映射表 (通用)
RENAME_MAP = {
    "香港": "HK",
    "美国": "US",
    "新加坡": "SG",
    "日本": "JP",
    "家宽": "ISP",
}

# 2. 区域白名单
SHARED_KEYWORDS = [
    "US",
    "HK",
    "Hong Kong",
    "Singapore",
    "Japan",
    "United States",
    "SG",
    "JP",
    "美国",
    "香港",
    "新加坡",
    "日本",
]

# 3. 排除黑名单
SHARED_EXCLUDE_KEYWORDS = [
    "官网",
    "流量",
    "倍率",
    "剩余",
    "Australia",
    "到期",
    "重置",
    "HK3-HY2",
    "HK4-HY2",
    "HK5-HY2",
]

# ================= [Clash] 专用配置 =================

CLASH_TEMPLATE_PC = Path("pc.yaml")
CLASH_TEMPLATE_MTUN = Path("mtun.yaml")
CLASH_TEMPLATE_OPENWRT = Path("openwrt.yaml")
CLASH_TEMPLATE_M = Path("m.yaml")

CLASH_USER_AGENT = "clash-verge"
CLASH_INCLUDED_HEADERS = ["Subscription-Userinfo"]
CLASH_HY2_UP = "40 Mbps"
CLASH_HY2_DOWN = "100 Mbps"
CLASH_HY2_UP_M = "30 Mbps"
CLASH_HY2_DOWN_M = "60 Mbps"
CLASH_FINGERPRINT = "firefox"

# ================= [Sing-box] 专用配置 =================

SB_TEMPLATE_MAP = {
    "openwrt": "openwrt.json",
    "pc": "pc.json",
    "mtun": "mtun.json",
    "m": "m.json",
}

# ================= 日志配置 =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ================= 通用辅助函数 =================


def read_url_from_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                return url
    raise ValueError(f"URL [None]: {path}")


def clean_node_name(name: str) -> str:
    """[复用] 清洗节点名称"""
    if not name:
        return name
    for k, v in RENAME_MAP.items():
        name = name.replace(k, v)
    name = re.sub(r"[^\x00-\x7F]+", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


# ==============================================================================
# PART 1: Clash 处理逻辑
# ==============================================================================


def is_valid_clash_yaml(text: str) -> bool:
    if not text:
        return False
    return "proxies:" in text


def save_headers_to_disk(source_name, headers):
    try:
        filtered = {
            k: v
            for k, v in headers.items()
            if k.lower() in {h.lower() for h in CLASH_INCLUDED_HEADERS}
        }
        if not filtered:
            return {}
        file_path = CACHE_DIR / f"{source_name}.headers.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        return filtered
    except Exception as e:
        logger.error(f"save Headers Error: {e}")
        return {}


def load_headers_from_disk(source_name):
    file_path = CACHE_DIR / f"{source_name}.headers.json"
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_yaml_text_clash(url, source_name, force_refresh=False):
    yaml_cache_file = CACHE_DIR / f"{source_name}.yaml"

    # 1. 优先检查缓存
    # 条件: 没有强制刷新 AND 文件存在
    if not force_refresh and yaml_cache_file.exists():
        try:
            mtime = os.path.getmtime(yaml_cache_file)
            # 检查是否过期
            if time.time() - mtime < CACHE_EXPIRE_SECONDS:
                logger.info(f"[{source_name}] [Clash] [cache] [Skip]")
                with open(yaml_cache_file, "r", encoding="utf-8") as f:
                    return f.read(), load_headers_from_disk(source_name)
        except Exception as e:
            logger.warning(f"读取缓存属性失败，将尝试网络请求: {e}")

    if force_refresh:
        logger.info(f"[{source_name}] [Clash] [Received u]")

    # 2. 网络请求
    try:
        headers = {"User-Agent": CLASH_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        text_content = response.text.lstrip("\ufeff").replace("\r\n", "\n")

        if is_valid_clash_yaml(text_content):
            save_headers_to_disk(source_name, response.headers)
            with open(yaml_cache_file, "w", encoding="utf-8") as f:
                f.write(text_content)
            logger.info(f"[{source_name}] [Clash] Updated Successfully")
            return text_content, response.headers
        else:
            logger.warning(f"[{source_name}] [Clash] [Fetch Error] [Fallback To Cache]")
    except Exception as e:
        logger.error(f"[{source_name}] [Clash] [Updated Error]: {e}")

    # 3. [兜底] 灾难恢复：如果网络失败，强制读取旧缓存 (不管有没有过期)
    if yaml_cache_file.exists():
        logger.info(f"[{source_name}] [Clash] [Loaded cache] [Fallback]")
        with open(yaml_cache_file, "r", encoding="utf-8") as f:
            return f.read(), load_headers_from_disk(source_name)

    raise RuntimeError(f"[{source_name}] [Error]")


def filter_node_names_clash(proxies):
    all_names = [p.get("name") for p in proxies if isinstance(p, dict) and "name" in p]
    filtered = [
        n
        for n in all_names
        if any(kw.lower() in n.lower() for kw in SHARED_KEYWORDS)
        and not any(ex.lower() in n.lower() for ex in SHARED_EXCLUDE_KEYWORDS)
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
    yaml_text: str, template_path: Path, up_pref: str, down_pref: str
):
    try:
        input_data = yaml.safe_load(yaml_text)
        if not isinstance(input_data, dict):
            raise ValueError("[Invalid YAML Format]")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.safe_load(f)

        proxies_orig = input_data.get("proxies", [])

        filtered_names, _ = filter_node_names_clash(proxies_orig)

        final_proxies = []
        for p in proxies_orig:
            if isinstance(p, dict) and p.get("name") in filtered_names:
                p["name"] = clean_node_name(p["name"])
                process_proxy_config_clash(p, up_pref, down_pref)
                final_proxies.append(p)

        if not final_proxies and proxies_orig:
            logger.warning("[Node None] [Fallback To All Nodes]")
            for p in proxies_orig:
                if isinstance(p, dict):
                    p["name"] = clean_node_name(p.get("name", ""))
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
                    pattern = group["filter"]
                    del group["filter"]
                    group.pop("include-all-proxies", None)
                    try:
                        matcher = re.compile(pattern, re.IGNORECASE)
                        matched_proxies = [
                            n for n in all_node_names if matcher.search(n)
                        ]
                        if matched_proxies:
                            group["proxies"] = matched_proxies
                            temp_groups.append(group)
                    except Exception as e:
                        logger.error(f"分组 {group.get('name')} 正则错误: {e}")
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


# ==============================================================================
# PART 2: Sing-box 处理逻辑
# ==============================================================================


def process_shadowsocks_sb(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "shadowsocks"
    node["server_port"] = int(proxy["port"])
    node["method"] = proxy.get("cipher")
    node["password"] = proxy.get("password")
    if "plugin" in proxy:
        plugin = proxy.get("plugin")
        plugin_opts = proxy.get("plugin-opts", {})
        if plugin == "obfs":
            node["plugin"] = "obfs-local"
            mode = plugin_opts.get("mode", "http")
            host = plugin_opts.get("host", "")
            node["plugin_opts"] = f"obfs={mode};obfs-host={host}"
    return node


def process_vless_sb(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "vless"
    node["server_port"] = int(proxy["port"])
    node["uuid"] = proxy.get("uuid")
    node["flow"] = proxy.get("flow", "")
    if "packet-encoding" in proxy:
        node["packet_encoding"] = proxy["packet-encoding"]
    network = proxy.get("network", "tcp")
    transport = {}
    if network == "ws":
        transport["type"] = "ws"
        ws_opts = proxy.get("ws-opts", {})
        transport["path"] = ws_opts.get("path", "/")
        if "headers" in ws_opts and "Host" in ws_opts["headers"]:
            transport["headers"] = {"Host": ws_opts["headers"]["Host"]}
    elif network == "grpc":
        transport["type"] = "grpc"
        grpc_opts = proxy.get("grpc-opts", {})
        transport["service_name"] = grpc_opts.get("grpc-service-name", "")
    if transport:
        node["transport"] = transport
    if proxy.get("tls") or proxy.get("reality-opts"):
        tls = {
            "enabled": True,
            "insecure": proxy.get("skip-cert-verify", False),
            "server_name": proxy.get("servername", ""),
        }
        if "reality-opts" in proxy:
            reality_opts = proxy.get("reality-opts", {})
            tls["reality"] = {
                "enabled": True,
                "public_key": reality_opts.get("public-key"),
                "short_id": reality_opts.get("short-id"),
            }
            if not tls["server_name"]:
                tls["server_name"] = proxy.get("sni", "")
        tls["utls"] = {"enabled": True, "fingerprint": "firefox"}
        node["tls"] = tls
    return node


def process_hysteria2_sb(
    proxy: Dict[str, Any], base_node: Dict[str, Any]
) -> Dict[str, Any]:
    node = base_node.copy()
    node["type"] = "hysteria2"
    node["password"] = proxy.get("password")
    if "ports" in proxy:
        node["server_ports"] = proxy["ports"]
    elif "port" in proxy:
        node["server_port"] = int(proxy["port"])
    node["up_mbps"] = 40
    node["down_mbps"] = 100
    if "obfs" in proxy:
        node["obfs"] = {
            "type": "salamander",
            "password": proxy.get("obfs-password", ""),
        }
    tls = {
        "enabled": True,
        "insecure": proxy.get("skip-cert-verify", False),
        "server_name": proxy.get("sni", ""),
    }
    node["tls"] = tls
    return node


def clash_to_singbox(proxy: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    p_type = proxy.get("type", "").lower()
    base_node = {"tag": proxy.get("name"), "server": proxy.get("server")}
    if p_type == "ss":
        return process_shadowsocks_sb(proxy, base_node)
    elif p_type == "vless":
        return process_vless_sb(proxy, base_node)
    elif p_type == "hysteria2":
        return process_hysteria2_sb(proxy, base_node)
    else:
        return None


def fetch_and_process_singbox(source: str, config_param: str, force_refresh=False):
    path = source_map.get(source)
    url = read_url_from_file(path)
    cache_file_path = CACHE_DIR / f"{source}.yaml"

    yaml_content = ""
    used_cache = False

    # 1. 优先检查缓存
    # 条件: 没有强制刷新 AND 文件存在
    if not force_refresh and cache_file_path.exists():
        try:
            mtime = os.path.getmtime(cache_file_path)
            if time.time() - mtime < CACHE_EXPIRE_SECONDS:
                logger.info(f"[{source}] [Sing-Box] [cache] [Skip]")
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    yaml_content = f.read()
                used_cache = True
        except Exception:
            pass

    if force_refresh:
        logger.info(f"[{source}] [Sing-Box] [Received u]")

    # 2. 网络请求
    if not used_cache:
        try:
            headers = {"User-Agent": "clash-verge"}
            logger.info(f"[{source}] [Sing-Box] [Fetching ...]")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            temp_content = response.text.strip()
            if "proxies:" not in temp_content:
                raise ValueError("[Invalid Clash YAML Content]")

            yaml_content = temp_content
            # 更新缓存
            with open(cache_file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            logger.info(f"[{source}] [Sing-Box] [Updated Successfully]")

        except Exception as e:
            logger.error(f"[{source}] [Sing-Box] [Error] [Try Cache] {e}")
            # 3. [兜底] 网络失败，尝试读取旧缓存
            if cache_file_path.exists():
                logger.warning(f"[{source}] [Sing-Box] 使用过期缓存兜底")
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    yaml_content = f.read()
            else:
                return jsonify({"error": f"[{source}] [Fetch Error]"}), 500

    try:
        try:
            clash_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as ye:
            return jsonify({"error": f"YAML 解析失败: {str(ye)}"}), 400

        if not isinstance(clash_data, dict) or "proxies" not in clash_data:
            return jsonify({"error": "无效的 Clash 配置"}), 400

        raw_proxies = clash_data["proxies"]
        nodes = []
        for proxy in raw_proxies:
            try:
                original_name = proxy.get("name", "")
                if any(ex in original_name for ex in SHARED_EXCLUDE_KEYWORDS):
                    continue

                proxy["name"] = clean_node_name(original_name)
                sb_node = clash_to_singbox(proxy)
                if sb_node:
                    nodes.append(sb_node)
            except Exception:
                continue

        if not nodes:
            return jsonify({"error": "没有转换成功的节点"}), 400

        template_filename = SB_TEMPLATE_MAP.get(
            config_param, SB_TEMPLATE_MAP["openwrt"]
        )
        if not os.path.exists(template_filename):
            return jsonify({"error": f"模板文件未找到: {template_filename}"}), 500

        with open(template_filename, "r", encoding="utf-8") as f:
            base_config = json.load(f)

        outbounds = base_config.get("outbounds", [])
        existing_tags = {o.get("tag") for o in outbounds}
        new_nodes = [
            n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags
        ]
        outbounds.extend(new_nodes)

        def node_tag_valid(tag: str) -> bool:
            tag_upper = tag.upper() if tag else ""
            if not any(region.upper() in tag_upper for region in SHARED_KEYWORDS):
                return False
            if any(exclude in tag for exclude in SHARED_EXCLUDE_KEYWORDS):
                return False
            return True

        filtered_outbounds = [
            o
            for o in outbounds
            if node_tag_valid(o.get("tag", ""))
            or o.get("type") in ["urltest", "selector", "direct", "block", "dns"]
        ]

        temp_outbounds = []
        all_node_tags = [
            o.get("tag")
            for o in filtered_outbounds
            if o.get("type") not in ["urltest", "selector", "direct", "block", "dns"]
        ]

        for outbound in filtered_outbounds:
            if outbound.get("type") in ["urltest", "selector"] and "filter" in outbound:
                regex_list = [
                    reg
                    for f in outbound.get("filter", [])
                    for reg in f.get("regex", [])
                ]
                del outbound["filter"]
                if not regex_list:
                    continue
                pattern = "|".join(regex_list)
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    matched_tags = [
                        tag for tag in all_node_tags if compiled.search(tag)
                    ]
                    if matched_tags:
                        outbound["outbounds"] = matched_tags
                        temp_outbounds.append(outbound)
                except re.error as e:
                    logger.error(f"无效的正则表达式: {e}")
            else:
                temp_outbounds.append(outbound)

        final_outbounds = []
        surviving_tags = {o.get("tag") for o in temp_outbounds if o.get("tag")}

        for outbound in temp_outbounds:
            if "outbounds" in outbound and isinstance(outbound["outbounds"], list):
                original_refs = outbound["outbounds"]
                cleaned_refs = [tag for tag in original_refs if tag in surviving_tags]
                outbound["outbounds"] = cleaned_refs
                if not cleaned_refs:
                    continue
            final_outbounds.append(outbound)

        for outbound in final_outbounds:
            if outbound.get("type") == "selector":
                current_outbounds = outbound.get("outbounds", [])
                current_default = outbound.get("default", "")
                if current_outbounds and current_default not in current_outbounds:
                    outbound["default"] = current_outbounds[0]

        base_config["outbounds"] = final_outbounds
        json_str = json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))
        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=config.json"},
        )

    except Exception as e:
        logger.error(f"Singbox 处理内部错误: {e}")
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500


# ==============================================================================
# PART 3: 路由入口
# ==============================================================================


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

    # 极简模式：只要 URL 包含 &u 参数，就强制刷新
    is_force_refresh = "u" in request.args

    # ============ 1. 优先检查 Sing-box 客户端 (Map 模式) ============

    # 映射表: {UA关键词: 模板名称}
    # Python 3.7+ 字典有序，匹配顺序即为定义顺序
    singbox_ua_map = {
        "SFA": "mtun",
        "sing-box_openwrt": "openwrt",
        "sing-box_m": "m",
        "sing-box_pc": "pc",
    }

    for keyword, config_val in singbox_ua_map.items():
        if keyword in ua:
            logger.info(
                f"[Sing-Box] | [Template: {config_val}] | [Force update: {is_force_refresh}] | [UA: {ua}]"
            )
            return fetch_and_process_singbox(
                source, config_val, force_refresh=is_force_refresh
            )

    # 2. 检查 Clash 客户端
    config_val = None

    if "ClashMetaForAndroid" in ua:
        config_val = "mtun"
    elif "clash_pc" in ua:
        config_val = "pc"
    elif "clash_openwrt" in ua:
        config_val = "openwrt"
    elif "clash_m" in ua:
        config_val = "m"
    else:
        abort(404)

    config_map = {
        "m": (CLASH_TEMPLATE_M, CLASH_HY2_UP_M, CLASH_HY2_DOWN_M),
        "mtun": (CLASH_TEMPLATE_MTUN, CLASH_HY2_UP_M, CLASH_HY2_DOWN_M),
        "pc": (CLASH_TEMPLATE_PC, CLASH_HY2_UP, CLASH_HY2_DOWN),
        "openwrt": (CLASH_TEMPLATE_OPENWRT, CLASH_HY2_UP, CLASH_HY2_DOWN),
    }

    template_path, up, down = config_map[config_val]
    logger.info(
        f"[Clash] | [Template: {config_val}] | [Force update: {is_force_refresh}] | [UA: {ua}]"
    )

    try:
        url = read_url_from_file(path)
        # 传递 force_refresh 参数
        yaml_text, headers_data = fetch_yaml_text_clash(
            unquote(url), source, force_refresh=is_force_refresh
        )
        output_bytes = process_yaml_content_clash(yaml_text, template_path, up, down)

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
        logger.error(f"Clash [Error]: {e}")
        return str(e), 500


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
