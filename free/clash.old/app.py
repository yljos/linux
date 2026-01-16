from flask import Flask, send_file, request
from ruamel.yaml import YAML
import requests
from urllib.parse import unquote
from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import hmac
import io
from threading import RLock


# =====================
# .env 配置项直接常量化
# =====================
app = Flask(__name__)


TEMPLATE_PATH_PC = Path("b.yaml")
TEMPLATE_PATH_M = Path("b_shouji.yaml")
HEADERS_CACHE = {}
HEADERS_CACHE_LOCK = RLock()

USER_AGENT = "clash verge"
CACHE_DURATION = 300
HYSTERIA2_UP = "40 Mbps"
HYSTERIA2_DOWN = "200 Mbps"
HYSTERIA2_UP_M = "20 Mbps"
HYSTERIA2_DOWN_M = "40 Mbps"
INCLUDED_HEADERS = set("Subscription-Userinfo".split(","))

NODE_KEYWORDS = [
    k.strip() for k in "US,HK,SG,JP,美国,香港,新加坡,日本".split(",") if k.strip()
]
NODE_EXCLUDE_KEYWORDS = [
    k.strip() for k in "官网,流量,倍率,剩余,10,到期".split(",") if k.strip()
]

ENABLE_NODE_REPLACEMENT = False
CLIENT_FINGERPRINT = "firefox"

MITCE_URL_FILE = Path("mitce").absolute()
BAJIE_URL_FILE = Path("bajie").absolute()
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"

DEBUG = True
PORT = 5002
HOST = "0.0.0.0"


"""
仅内存缓存：不再使用基于文件的 headers 缓存
（已在常量区定义）
"""

# 验证必要文件存在
if not TEMPLATE_PATH_PC.exists():
    raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_PATH_PC}")
if not TEMPLATE_PATH_M.exists():
    raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_PATH_M}")

# 验证 URL 文件存在
for _path in (MITCE_URL_FILE, BAJIE_URL_FILE):
    if not _path.exists():
        raise FileNotFoundError(f"URL 文件不存在: {_path}")


def read_url_from_file(path: Path) -> str:
    """从文本文件读取上游 URL，取第一行非空内容。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if url:
                    return url
        raise ValueError(f"URL 文件为空: {path}")
    except Exception as e:
        raise RuntimeError(f"读取 URL 文件失败 {path}: {e}")


@app.before_request
def restrict_paths():
    # 允许的路径集合
    allowed = {"/mitce", "/bajie"}
    if request.path not in allowed:
        return "Not Found", 404
    # 查询参数中携带 key 进行鉴权
    key = request.args.get("key")
    if not key:
        return "Unauthorized", 401
    provided_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(provided_hash, ACCESS_KEY_SHA256):
        return "Unauthorized", 401


# YAML 配置
def setup_yaml_config():
    """设置YAML配置"""
    yaml_config = YAML()
    yaml_config.preserve_quotes = True
    yaml_config.indent(mapping=2, sequence=2, offset=2)
    yaml_config.width = 4096  # 避免自动换行
    # 使字典以流式风格(单行 {}) 输出
    yaml_config.default_flow_style = None
    return yaml_config


def set_flow_style_for_proxies(proxies_list):
    """将代理列表中的每个映射设置为 flow style（{ ... }）。
    仅在使用 ruamel.dump 时生效。失败时静默跳过，保持默认格式。"""
    for item in proxies_list:
        try:
            # ruamel 的 CommentedMap 支持通过 .fa.set_flow_style() 设置为 flow style
            if hasattr(item, "fa") and hasattr(item.fa, "set_flow_style"):
                item.fa.set_flow_style()
        except Exception:
            continue


yaml = setup_yaml_config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_headers_cache(url, headers):
    """保存请求头缓存到内存，仅保存白名单中的 header。"""
    try:
        filtered_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() in {h.lower() for h in INCLUDED_HEADERS}
        }

        with HEADERS_CACHE_LOCK:
            HEADERS_CACHE[url] = {
                "headers": filtered_headers,
                "timestamp": datetime.now(),
            }
    except Exception as e:
        logger.error(f"保存headers内存缓存失败: {e}")


def get_headers_cache(url):
    """获取指定 URL 的 headers 内存缓存，检查是否过期。"""
    try:
        with HEADERS_CACHE_LOCK:
            entry = HEADERS_CACHE.get(url)
            if not entry:
                return None

            cache_time = entry.get("timestamp")
            if datetime.now() - cache_time < timedelta(seconds=CACHE_DURATION):
                return entry.get("headers")
            else:
                # 过期清理
                HEADERS_CACHE.pop(url, None)
                return None
    except Exception as e:
        logger.error(f"读取headers内存缓存失败: {e}")
        return None


def fetch_yaml_text(url):
    """获取上游 YAML 文本并缓存响应头（内存模式）。"""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        save_headers_cache(url, response.headers)
        logger.info("成功获取上游YAML文本")
        return response.text
    except Exception as e:
        logger.error(f"获取YAML失败: {str(e)}")
        raise


def filter_node_names(proxies):
    """在内存中过滤节点名称，返回 (filtered_node_names, all_node_names)。"""
    all_names = [
        proxy.get("name")
        for proxy in proxies
        if isinstance(proxy, dict) and "name" in proxy
    ]
    filtered = [
        n
        for n in all_names
        if any(kw.lower() in n.lower() for kw in NODE_KEYWORDS)
        and not any(ex.lower() in n.lower() for ex in NODE_EXCLUDE_KEYWORDS)
    ]
    logger.info(
        (
            "节点过滤完成: 过滤 %d / 原始 %d 包含=%s 排除=%s"
            % (len(filtered), len(all_names), NODE_KEYWORDS, NODE_EXCLUDE_KEYWORDS)
        )
    )
    return filtered, all_names


def filter_nodes_by_region(node_names, region_patterns):
    """根据区域模式筛选节点"""
    filtered_nodes = []
    for name in node_names:
        for pattern in region_patterns:
            if pattern in name.upper() or any(
                chinese in name for chinese in region_patterns if len(chinese) > 2
            ):
                if name not in [
                    p.upper() for p in region_patterns if len(p) <= 3
                ]:  # 排除简单的区域代码
                    filtered_nodes.append(name)
                    break
    return list(dict.fromkeys(filtered_nodes))  # 去重


def replace_fallback_nodes_in_group(
    proxies, fallback_name, replacement_nodes, group_name
):
    """在代理组中替换fallback节点"""
    if fallback_name in proxies and replacement_nodes:
        index = proxies.index(fallback_name)
        filtered_nodes = [node for node in replacement_nodes if node not in proxies]

        if filtered_nodes:
            proxies.pop(index)
            for i, node in enumerate(filtered_nodes):
                proxies.insert(index + i, node)
            logger.info(
                f"在代理组 '{group_name}' 中替换{fallback_name}为 {len(filtered_nodes)} 个实际节点"
            )


def process_proxy_config(proxy, up_pref: str, down_pref: str):
    """处理单个代理配置"""
    if not isinstance(proxy, dict):
        return

    proxy_type = proxy.get("type")

    if proxy_type == "hysteria2":
        # 确保带宽值包含单位
        up_value = up_pref if "bps" in up_pref.lower() else f"{up_pref} Mbps"
        down_value = down_pref if "bps" in down_pref.lower() else f"{down_pref} Mbps"

        proxy.update({"up": up_value, "down": down_value, "skip-cert-verify": False})

    elif proxy_type == "vless":
        proxy.update({"skip-cert-verify": False, "packet-encoding": "xudp"})

        # 仅在 vless 类型下，如果存在 client-fingerprint 键，则统一替换为 firefox
        try:
            if "client-fingerprint" in proxy:
                proxy["client-fingerprint"] = CLIENT_FINGERPRINT

        except Exception:
            logger.debug("在 vless 中设置 client-fingerprint 时发生异常")


def replace_proxy_groups_with_nodes(template_data, node_names):
    """用内存节点列表替换 fallback 组中的占位节点。"""
    if not node_names:
        logger.info("无可用节点名称，跳过代理组替换。")
        return template_data

    region_configs = {
        "US_fallback": (["US", "美国"], "US"),
        "HK_fallback": (["HK", "香港"], "HK"),
        "SG_fallback": (["SG", "新加坡", "Singapore"], "SG"),
        "JP_fallback": (["JP", "日本", "Japan"], "JP"),
        "TW_fallback": (["TW", "台湾", "Taiwan"], "TW"),
    }

    region_nodes = {}
    for fallback_key, (patterns, _) in region_configs.items():
        region_nodes[fallback_key] = filter_nodes_by_region(node_names, patterns)
        logger.info(
            f"找到 {len(region_nodes[fallback_key])} 个{fallback_key.replace('_fallback', '')}节点"
        )

    proxy_groups = template_data.get("proxy-groups", [])
    for group in proxy_groups:
        if (
            isinstance(group, dict)
            and group.get("type") == "fallback"
            and "proxies" in group
        ):
            group_name = group.get("name", "未命名")
            proxies = group["proxies"]
            for fallback_name, nodes in region_nodes.items():
                replace_fallback_nodes_in_group(
                    proxies, fallback_name, nodes, group_name
                )
    return template_data


def process_yaml_content(
    yaml_text: str, template_path: Path, up_pref: str, down_pref: str
):
    """处理上游YAML文本，返回字节串以便内存直传。"""
    try:
        # 解析YAML获取数据结构（直接从字符串）
        input_data = yaml.load(yaml_text)

        if not isinstance(input_data, dict):
            raise ValueError("YAML内容必须是有效的字典格式")

        # 读取标准模板
        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.load(f)

        proxies_original = input_data.get("proxies", [])
        if not proxies_original:
            raise ValueError("YAML文件中未找到有效的proxies配置")

        # 处理原始代理配置（仅用于生成/过滤节点名称）
        for proxy in proxies_original:
            process_proxy_config(proxy, up_pref, down_pref)

        # 内存过滤节点
        filtered_names, all_names = filter_node_names(proxies_original)

        proxies = [
            p
            for p in proxies_original
            if isinstance(p, dict) and p.get("name") in filtered_names
        ]
        if not proxies:
            logger.warning("过滤后无匹配节点，使用全部原始节点 (0 filtered)")
            proxies = proxies_original

        if ENABLE_NODE_REPLACEMENT:
            template_data = replace_proxy_groups_with_nodes(
                template_data, filtered_names
            )

        # 内存中生成 YAML 文本
        buf = io.StringIO()
        template_data["proxies"] = proxies
        set_flow_style_for_proxies(template_data.get("proxies", []))
        yaml.dump(template_data, buf)
        text = buf.getvalue()
        return text.encode("utf-8")

    except Exception as e:
        logger.error(f"处理YAML内容失败: {str(e)}")
        raise


# 合并 mitce 和 bajie 路由为 /<source>
@app.route("/<source>")
def process_source(source):
    try:
        if source == "mitce":
            yaml_url = unquote(read_url_from_file(MITCE_URL_FILE))
        elif source == "bajie":
            yaml_url = unquote(read_url_from_file(BAJIE_URL_FILE))
        else:
            return "Not Found", 404

        config_val = (request.args.get("config", "pc") or "pc").lower()
        template_path = TEMPLATE_PATH_M if config_val == "m" else TEMPLATE_PATH_PC
        up_pref = HYSTERIA2_UP_M if config_val == "m" else HYSTERIA2_UP
        down_pref = HYSTERIA2_DOWN_M if config_val == "m" else HYSTERIA2_DOWN
        logger.info(f"处理URL({source}) 使用模板: {template_path}")

        yaml_text = fetch_yaml_text(yaml_url)
        output_bytes = process_yaml_content(
            yaml_text, template_path, up_pref, down_pref
        )
        cached_headers = get_headers_cache(yaml_url)

        response = send_file(
            io.BytesIO(output_bytes),
            mimetype="application/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )

        response.headers["Content-Type"] = "application/yaml; charset=utf-8"

        if cached_headers:
            for header, value in cached_headers.items():
                if header.lower() in {h.lower() for h in INCLUDED_HEADERS}:
                    response.headers[header] = value
        return response

    except Exception as e:
        logger.error(f"处理请求失败({source}): {str(e)}")
        return str(e), 500


if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host=HOST)
