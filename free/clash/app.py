import re
from flask import Flask, send_file, request, abort
import yaml as pyyaml
import requests
from urllib.parse import unquote
import logging
from pathlib import Path
import hashlib
import hmac
import io
import json

app = Flask(__name__)

# ================= 配置区域 =================

TEMPLATE_PATH_PC = Path("pc.yaml")
TEMPLATE_PATH_MTUN = Path("mtun.yaml")
TEMPLATE_PATH_OPENWRT = Path("openwrt.yaml")
TEMPLATE_PATH_M = Path("m.yaml")

USER_AGENT = "clash-verge"
HYSTERIA2_UP = "40 Mbps"
HYSTERIA2_DOWN = "200 Mbps"
HYSTERIA2_UP_M = "30 Mbps"
HYSTERIA2_DOWN_M = "60 Mbps"
INCLUDED_HEADERS = ["Subscription-Userinfo"]

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# 1. 包含关键词 (保留这些区域)
raw_keywords = (
    "US,HK,Hong Kong,Singapore,Japan,United States,SG,JP,美国,香港,新加坡,日本"
)
NODE_KEYWORDS = [k.strip() for k in raw_keywords.split(",") if k.strip()]

# 2. 排除关键词 (在这里维护你的黑名单)
raw_exclude = "官网,流量,倍率,剩余,Australia,到期,HK3-HY2,HK4-HY2,HK5-HY2"
NODE_EXCLUDE_KEYWORDS = [k.strip() for k in raw_exclude.split(",") if k.strip()]

# 3. 节点重命名映射表 (中文 -> 英文)
RENAME_MAP = {
    "香港": "HK",
    "美国": "US",
    "新加坡": "SG",
    "日本": "JP",
    "家宽": "Home",
}

CLIENT_FINGERPRINT = "firefox"
MITCE_URL_FILE = Path("mitce").absolute()
BAJIE_URL_FILE = Path("bajie").absolute()
source_map = {
    "mitce": MITCE_URL_FILE,
    "bajie": BAJIE_URL_FILE,
}
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"

# ================= 日志配置 =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ================= 辅助函数 =================


def read_url_from_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                return url
    raise ValueError(f"URL 文件为空: {path}")


def is_valid_clash_yaml(text: str) -> bool:
    """仅通过标准关键字 proxies: 判断有效性"""
    if not text:
        return False
    return "proxies:" in text


def clean_node_name(name: str) -> str:
    """清洗节点名称：替换国家名 -> 移除图标/特殊字符 -> 去空格"""
    if not name:
        return name

    # 1. 关键词替换 (中文 -> 英文)
    for k, v in RENAME_MAP.items():
        name = name.replace(k, v)

    # 2. 移除所有非 ASCII 字符 (暴力去除图标、旗帜、剩余中文)
    # [^\x00-\x7F] 匹配所有非英文字符
    name = re.sub(r"[^\x00-\x7F]+", "", name)

    # 3. 清理多余空格 (例如 "US   Node" -> "US Node")
    name = re.sub(r"\s+", " ", name).strip()

    return name


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


def save_headers_to_disk(source_name, headers):
    try:
        filtered = {
            k: v
            for k, v in headers.items()
            if k.lower() in {h.lower() for h in INCLUDED_HEADERS}
        }
        if not filtered:
            return {}
        file_path = CACHE_DIR / f"{source_name}.headers.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        return filtered
    except Exception as e:
        logger.error(f"保存 Headers 失败: {e}")
        return {}


def load_headers_from_disk(source_name):
    file_path = CACHE_DIR / f"{source_name}.headers.json"
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_yaml_text(url, source_name):
    yaml_cache_file = CACHE_DIR / f"{source_name}.yaml"

    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        text_content = response.text.lstrip("\ufeff").replace("\r\n", "\n")

        # 校验：包含 proxies: 关键字才更新缓存
        if is_valid_clash_yaml(text_content):
            save_headers_to_disk(source_name, response.headers)
            with open(yaml_cache_file, "w", encoding="utf-8") as f:
                f.write(text_content)
            logger.info(f"[{source_name}] 拉取成功并更新缓存")
            return text_content, response.headers
        else:
            logger.warning(f"[{source_name}] 拉取失败,启用灾难缓存")

    except Exception as e:
        logger.error(f"[{source_name}] 网络拉取失败: {e}")

    if yaml_cache_file.exists():
        logger.info(f"[{source_name}] 载入缓存成功")
        with open(yaml_cache_file, "r", encoding="utf-8") as f:
            return f.read(), load_headers_from_disk(source_name)

    raise RuntimeError(f"[{source_name}] 获取失败且无本地缓存")


def filter_node_names(proxies):
    """过滤逻辑：保留在白名单中 且 不在黑名单中的节点"""
    all_names = [p.get("name") for p in proxies if isinstance(p, dict) and "name" in p]
    filtered = [
        n
        for n in all_names
        if any(kw.lower() in n.lower() for kw in NODE_KEYWORDS)
        and not any(ex.lower() in n.lower() for ex in NODE_EXCLUDE_KEYWORDS)
    ]
    return filtered, all_names


def process_proxy_config(proxy, up_pref, down_pref):
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
            proxy["client-fingerprint"] = CLIENT_FINGERPRINT


def process_yaml_content(
    yaml_text: str, template_path: Path, up_pref: str, down_pref: str
):
    try:
        input_data = pyyaml.safe_load(yaml_text)
        if not isinstance(input_data, dict):
            raise ValueError("无效的YAML格式")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = pyyaml.safe_load(f)

        proxies_orig = input_data.get("proxies", [])

        # 1. 先进行过滤（确保基于原始名字剔除垃圾节点，如"官网"、"剩余"等）
        filtered_names, _ = filter_node_names(proxies_orig)

        final_proxies = []
        for p in proxies_orig:
            # 只处理被筛选留下的节点
            if isinstance(p, dict) and p.get("name") in filtered_names:
                # 2. 清洗名字 (中文转英文 + 去除图标/非ASCII)
                p["name"] = clean_node_name(p["name"])

                # 3. 处理速度和其他配置
                process_proxy_config(p, up_pref, down_pref)
                final_proxies.append(p)

        # 灾难恢复：如果过滤完是空的，保留原始列表但进行清洗
        if not final_proxies and proxies_orig:
            logger.warning("过滤后节点为空，回退使用全部节点")
            for p in proxies_orig:
                if isinstance(p, dict):
                    p["name"] = clean_node_name(p.get("name", ""))
                    process_proxy_config(p, up_pref, down_pref)
            final_proxies = proxies_orig

        # 追加 dns-out
        final_proxies.append({"name": "dns-out", "type": "dns"})

        template_data["proxies"] = final_proxies

        output = pyyaml.dump(
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


@app.route("/<source>")
def process_source(source):
    try:
        path = source_map.get(source)
        if not path:
            abort(404)

        url = read_url_from_file(path)

        ua = request.headers.get("User-Agent", "")

        if "ClashMetaForAndroid" in ua:
            detected_config = "mtun"
        elif "clash_pc" in ua:
            detected_config = "pc"
        elif "clash_openwrt" in ua:
            detected_config = "openwrt"
        elif "clash_m" in ua:
            detected_config = "m"
        else:
            abort(404)

        config_val = request.args.get("config", detected_config)

        config_map = {
            "m": (TEMPLATE_PATH_M, HYSTERIA2_UP_M, HYSTERIA2_DOWN_M),
            "mtun": (TEMPLATE_PATH_MTUN, HYSTERIA2_UP_M, HYSTERIA2_DOWN_M),
            "pc": (TEMPLATE_PATH_PC, HYSTERIA2_UP, HYSTERIA2_DOWN),
            "openwrt": (TEMPLATE_PATH_OPENWRT, HYSTERIA2_UP, HYSTERIA2_DOWN),
        }

        if config_val not in config_map:
            abort(404)

        template_path, up, down = config_map[config_val]

        logger.info(
            f"请求拉取: {source} | 识别模板: {detected_config} | 指定模板: {config_val} | 最终模板: {template_path}"
        )

        yaml_text, headers_data = fetch_yaml_text(unquote(url), source)
        output_bytes = process_yaml_content(yaml_text, template_path, up, down)

        response = send_file(
            io.BytesIO(output_bytes),
            mimetype="text/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )

        if headers_data:
            for h, v in headers_data.items():
                if h.lower() in {ih.lower() for ih in INCLUDED_HEADERS}:
                    response.headers[h] = v
        return response
    except Exception as e:
        logger.error(f"处理请求失败: {e}")
        return str(e), 500


if __name__ == "__main__":
    app.run(debug=False, port=5002, host="0.0.0.0")
