from flask import Flask, send_file, request
from ruamel.yaml import YAML
import requests
from urllib.parse import unquote
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import hmac
import io
import json  # [新增] 引入json处理

# =====================
# .env 配置项
# =====================
load_dotenv()
app = Flask(__name__)

TEMPLATE_PATH_PC = Path("b.yaml")
TEMPLATE_PATH_M = Path("b_shouji.yaml")


USER_AGENT = os.getenv("USER_AGENT")
HYSTERIA2_UP = os.getenv("HYSTERIA2_UP")
HYSTERIA2_DOWN = os.getenv("HYSTERIA2_DOWN")
HYSTERIA2_UP_M = os.getenv("HYSTERIA2_UP_M")
HYSTERIA2_DOWN_M = os.getenv("HYSTERIA2_DOWN_M")
INCLUDED_HEADERS = os.getenv("INCLUDED_HEADERS").split(",")
# 本地文件缓存目录
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

NODE_KEYWORDS = [
    k.strip()
    for k in "US,HK,Hong Kong,Singapore,Japan,United States,SG,JP,美国,香港,新加坡,日本".split(
        ","
    )
    if k.strip()
]
NODE_EXCLUDE_KEYWORDS = [
    k.strip() for k in "官网,流量,倍率,剩余,10,Australia,到期".split(",") if k.strip()
]

ENABLE_NODE_REPLACEMENT = os.getenv("ENABLE_NODE_REPLACEMENT").lower() in ("true", "1")
CLIENT_FINGERPRINT = os.getenv("CLIENT_FINGERPRINT")

MITCE_URL_FILE = Path("mitce").absolute()
BAJIE_URL_FILE = Path("bajie").absolute()
WESTDATA_URL_FILE = Path("westdata").absolute()

ACCESS_KEY_SHA256 = os.getenv("ACCESS_KEY_SHA256")
DEBUG = False
PORT = 5002
HOST = "0.0.0.0"

# 验证必要文件存在
if not TEMPLATE_PATH_PC.exists():
    raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_PATH_PC}")
if not TEMPLATE_PATH_M.exists():
    raise FileNotFoundError(f"模板文件不存在: {TEMPLATE_PATH_M}")

for _path in (MITCE_URL_FILE, BAJIE_URL_FILE, WESTDATA_URL_FILE):
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
    allowed = {"/mitce", "/bajie", "/westdata"}
    if request.path not in allowed:
        return "Not Found", 404
    key = request.args.get("key")
    if not key:
        return "Unauthorized", 401
    provided_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(provided_hash, ACCESS_KEY_SHA256):
        return "Unauthorized", 401


# YAML 配置
def setup_yaml_config():
    yaml_config = YAML()
    yaml_config.preserve_quotes = True
    yaml_config.indent(mapping=2, sequence=2, offset=2)
    yaml_config.width = 4096
    yaml_config.default_flow_style = None
    return yaml_config


def set_flow_style_for_proxies(proxies_list):
    for item in proxies_list:
        try:
            if hasattr(item, "fa") and hasattr(item.fa, "set_flow_style"):
                item.fa.set_flow_style()
        except Exception:
            continue


yaml = setup_yaml_config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# [新增] Headers 缓存读写辅助函数
def save_headers_to_disk(source_name, headers):
    """过滤并保存 Headers 到磁盘 JSON 文件"""
    try:
        filtered_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() in {h.lower() for h in INCLUDED_HEADERS}
        }
        # 如果没有需要保存的 header，就不创建文件
        if not filtered_headers:
            return {}

        file_path = CACHE_DIR / f"{source_name}.headers.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(filtered_headers, f, ensure_ascii=False, indent=2)
        return filtered_headers
    except Exception as e:
        logger.error(f"[{source_name}] 保存 Headers 到磁盘失败: {e}")
        return {}


def load_headers_from_disk(source_name):
    """从磁盘 JSON 文件读取 Headers"""
    file_path = CACHE_DIR / f"{source_name}.headers.json"
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[{source_name}] 读取磁盘 Headers 失败: {e}")
        return {}


def fetch_yaml_text(url, source_name):
    """
    获取上游 YAML 文本和 Headers。
    返回: (yaml_text, headers_dict)
    """
    yaml_cache_file = CACHE_DIR / f"{source_name}.yaml"

    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # 1. 网络请求成功，保存 Headers 到磁盘 (JSON)
        saved_headers = save_headers_to_disk(source_name, response.headers)

        # 2. 保存 YAML 内容到磁盘
        try:
            with open(yaml_cache_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info(f"[{source_name}] 网络拉取成功，缓存已更新")
        except Exception as write_err:
            logger.error(f"[{source_name}] 写入 YAML 缓存失败: {write_err}")

        return response.text, saved_headers

    except Exception as e:
        logger.error(f"[{source_name}] 网络拉取失败: {str(e)}")

        # 3. 灾难恢复：尝试读取本地 YAML 和 Headers
        if yaml_cache_file.exists():
            try:
                logger.warning(f"[{source_name}] !!! 启用灾难恢复，使用本地缓存 !!!")

                # 读取 YAML
                with open(yaml_cache_file, "r", encoding="utf-8") as f:
                    cached_yaml = f.read()

                # 读取 Headers
                cached_headers = load_headers_from_disk(source_name)

                return cached_yaml, cached_headers

            except Exception as read_err:
                logger.error(f"[{source_name}] 读取本地缓存失败: {read_err}")
                raise e
        else:
            logger.error(f"[{source_name}] 无本地缓存可用")
            raise e


def filter_node_names(proxies):
    """在内存中过滤节点名称"""
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
    logger.info("节点过滤完成: 过滤 %d / 原始 %d" % (len(filtered), len(all_names)))
    return filtered, all_names


def filter_nodes_by_region(node_names, region_patterns):
    """根据区域模式筛选节点"""
    filtered_nodes = []
    for name in node_names:
        for pattern in region_patterns:
            if pattern in name.upper() or any(
                chinese in name for chinese in region_patterns if len(chinese) > 2
            ):
                if name not in [p.upper() for p in region_patterns if len(p) <= 3]:
                    filtered_nodes.append(name)
                    break
    return list(dict.fromkeys(filtered_nodes))


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


def process_proxy_config(proxy, up_pref: str, down_pref: str):
    """处理单个代理配置"""
    if not isinstance(proxy, dict):
        return

    proxy_type = proxy.get("type")

    if proxy_type == "hysteria2":
        up_value = up_pref if "bps" in up_pref.lower() else f"{up_pref} Mbps"
        down_value = down_pref if "bps" in down_pref.lower() else f"{down_pref} Mbps"
        proxy.update({"up": up_value, "down": down_value, "skip-cert-verify": False})

    elif proxy_type == "vless":
        proxy.update({"skip-cert-verify": False, "packet-encoding": "xudp"})
        try:
            if "client-fingerprint" in proxy:
                proxy["client-fingerprint"] = CLIENT_FINGERPRINT
        except Exception:
            pass


def replace_proxy_groups_with_nodes(template_data, node_names):
    """用内存节点列表替换 fallback 组中的占位节点。"""
    if not node_names:
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
    """处理上游YAML文本"""
    try:
        input_data = yaml.load(yaml_text)
        if not isinstance(input_data, dict):
            raise ValueError("YAML内容必须是有效的字典格式")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.load(f)

        proxies_original = input_data.get("proxies", [])
        if not proxies_original:
            raise ValueError("YAML文件中未找到有效的proxies配置")

        for proxy in proxies_original:
            process_proxy_config(proxy, up_pref, down_pref)

        filtered_names, all_names = filter_node_names(proxies_original)

        proxies = [
            p
            for p in proxies_original
            if isinstance(p, dict) and p.get("name") in filtered_names
        ]
        if not proxies:
            logger.warning("过滤后无匹配节点，使用全部原始节点")
            proxies = proxies_original

        if ENABLE_NODE_REPLACEMENT:
            template_data = replace_proxy_groups_with_nodes(
                template_data, filtered_names
            )

        buf = io.StringIO()
        template_data["proxies"] = proxies
        set_flow_style_for_proxies(template_data.get("proxies", []))
        yaml.dump(template_data, buf)
        text = buf.getvalue()
        return text.encode("utf-8")

    except Exception as e:
        logger.error(f"处理YAML内容失败: {str(e)}")
        raise


@app.route("/<source>")
def process_source(source):
    try:
        if source == "mitce":
            yaml_url = unquote(read_url_from_file(MITCE_URL_FILE))
        elif source == "bajie":
            yaml_url = unquote(read_url_from_file(BAJIE_URL_FILE))
        elif source == "westdata":
            yaml_url = unquote(read_url_from_file(WESTDATA_URL_FILE))
        else:
            return "Not Found", 404

        config_val = (request.args.get("config", "pc") or "pc").lower()
        template_path = TEMPLATE_PATH_M if config_val == "m" else TEMPLATE_PATH_PC
        up_pref = HYSTERIA2_UP_M if config_val == "m" else HYSTERIA2_UP
        down_pref = HYSTERIA2_DOWN_M if config_val == "m" else HYSTERIA2_DOWN
        logger.info(f"处理URL({source}) 使用模板: {template_path}")

        # [核心改动] 获取 YAML 和 Headers (优先网络，失败则走缓存)
        yaml_text, headers_data = fetch_yaml_text(yaml_url, source_name=source)

        output_bytes = process_yaml_content(
            yaml_text, template_path, up_pref, down_pref
        )

        response = send_file(
            io.BytesIO(output_bytes),
            mimetype="application/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )

        response.headers["Content-Type"] = "application/yaml; charset=utf-8"

        # [核心改动] 写入缓存的 Headers
        if headers_data:
            for header, value in headers_data.items():
                response.headers[header] = value

        return response

    except Exception as e:
        logger.error(f"处理请求失败({source}): {str(e)}")
        return str(e), 500


if __name__ == "__main__":
    app.run(debug=DEBUG, port=PORT, host=HOST)
