import hashlib
import hmac
import io
import json
import logging
import re
from pathlib import Path
from urllib.parse import unquote

import yaml
from flask import Flask, send_file, request, abort, Response, jsonify

# ================= 模块开关 =================
ENABLE_CLASH = True
ENABLE_SINGBOX = False

if ENABLE_CLASH:
    import clash

if ENABLE_SINGBOX:
    import singbox

app = Flask(__name__)

# ================= 鉴权与通用配置 =================
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"

# 获取当前脚本所在目录的绝对路径，确保稳定运行
BASE_DIR = Path(__file__).resolve().parent

CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

source_map = {
    "mitce": BASE_DIR / "mitce",
    "bajie": BASE_DIR / "bajie",
}

# 自定义节点文件路径
CUSTOM_CLASH_NODE = BASE_DIR / "node.yaml"
CUSTOM_SINGBOX_NODE = BASE_DIR / "node.json"

# 需要将自定义节点加入的组名 (根据你的模板修改)
TARGET_GROUPS = ["Google"]

# 指定需要插入自定义节点的客户端模板
INJECT_TEMPLATES = ["m", "openwrt"]

# ================= 关键词与黑名单 =================
RENAME_MAP = {
    "香港": "HK",
    "美国": "US",
    "新加坡": "SG",
    "日本": "JP",
    "家宽": "ISP",
}

SHARED_KEYWORDS = [
    "US",
    "HK",
    "SG",
    "JP",
    "Hong Kong",
    "Singapore",
    "Japan",
    "United States",
    "美国",
    "香港",
    "新加坡",
    "日本",
]

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

# ================= 日志与通用辅助函数 =================
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


def inject_custom_clash_node(
    yaml_bytes: bytes, node_path: Path, target_groups: list
) -> bytes:
    """合并自定义 Clash 节点（支持单节点字典或多节点列表）并加入指定策略组"""
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

        for node in nodes:
            if not isinstance(node, dict) or "name" not in node:
                continue
                
            node_name = node["name"]

            # 1. 节点列表追加
            config.setdefault("proxies", []).append(node)

            # 2. 策略组追加
            for group in config.get("proxy-groups", []):
                if group.get("name") in target_groups:
                    group.setdefault("proxies", []).append(node_name)

        return yaml.safe_dump(config, allow_unicode=True, sort_keys=False).encode(
            "utf-8"
        )
    except Exception as e:
        logger.error(f"[Clash] 自定义节点合并失败: {e}")
        return yaml_bytes


def inject_custom_singbox_node(
    json_str: str, node_path: Path, target_groups: list
) -> str:
    """合并自定义 Sing-box 节点（支持单节点字典或多节点列表）并加入指定出站组"""
    if not node_path.exists():
        return json_str

    try:
        with open(node_path, "r", encoding="utf-8") as f:
            custom_data = json.load(f)

        if not custom_data:
            return json_str

        # 统一转换为列表处理
        outbounds = custom_data if isinstance(custom_data, list) else [custom_data]
        config = json.loads(json_str)

        for outbound in outbounds:
            if not isinstance(outbound, dict) or "tag" not in outbound:
                continue
                
            node_tag = outbound["tag"]

            # 1. 出站列表追加
            config.setdefault("outbounds", []).append(outbound)

            # 2. 注入到 selector/urltest 组
            for cfg_outbound in config.get("outbounds", []):
                if cfg_outbound.get("tag") in target_groups and cfg_outbound.get("type") in [
                    "selector",
                    "urltest",
                ]:
                    cfg_outbound.setdefault("outbounds", []).append(node_tag)

        return json.dumps(config, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[Sing-box] 自定义节点合并失败: {e}")
        return json_str


# ================= 路由保护与分发 =================
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

    # --- 1. Sing-box 分发逻辑 ---
    if ENABLE_SINGBOX:
        singbox_ua_map = {
            "SFA": "mtun",
            "sing-box_openwrt": "openwrt",
            "sing-box_m": "m",
            "sing-box_pc": "pc",
        }

        for keyword, config_val in singbox_ua_map.items():
            if keyword in ua:
                logger.info(
                    f"[Sing-Box] | [Template: {config_val}] | [Force: {is_force_refresh}] | [UA: {ua}]"
                )
                try:
                    url = read_url_from_file(path)
                    json_str = singbox.fetch_and_process_singbox(
                        source,
                        config_val,
                        is_force_refresh,
                        url,
                        CACHE_DIR,
                        CACHE_EXPIRE_SECONDS,
                        SHARED_KEYWORDS,
                        SHARED_EXCLUDE_KEYWORDS,
                        clean_node_name,
                    )

                    # 仅在指定的模板中插入节点
                    if config_val in INJECT_TEMPLATES:
                        json_str = inject_custom_singbox_node(
                            json_str, CUSTOM_SINGBOX_NODE, TARGET_GROUPS
                        )

                    return Response(
                        json_str,
                        mimetype="application/json",
                        headers={
                            "Content-Disposition": "attachment; filename=config.json"
                        },
                    )
                except FileNotFoundError as e:
                    return jsonify({"error": str(e)}), 500
                except ValueError as e:
                    return jsonify({"error": str(e)}), 400
                except Exception as e:
                    logger.error(f"Singbox 处理内部错误: {e}")
                    return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

    # --- 2. Clash 分发逻辑 ---
    if ENABLE_CLASH:
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
                    clash.CLASH_TEMPLATE_M,
                    clash.CLASH_HY2_UP_M,
                    clash.CLASH_HY2_DOWN_M,
                ),
                "mtun": (
                    clash.CLASH_TEMPLATE_MTUN,
                    clash.CLASH_HY2_UP_M,
                    clash.CLASH_HY2_DOWN_M,
                ),
                "pc": (
                    clash.CLASH_TEMPLATE_PC,
                    clash.CLASH_HY2_UP,
                    clash.CLASH_HY2_DOWN,
                ),
                "openwrt": (
                    clash.CLASH_TEMPLATE_OPENWRT,
                    clash.CLASH_HY2_UP,
                    clash.CLASH_HY2_DOWN,
                ),
            }

            template_path, up, down = config_map[clash_config_val]
            logger.info(
                f"[Clash] | [Template: {clash_config_val}] | [Force: {is_force_refresh}] | [UA: {ua}]"
            )

            try:
                url = read_url_from_file(path)
                yaml_text, headers_data = clash.fetch_yaml_text_clash(
                    unquote(url),
                    source,
                    is_force_refresh,
                    CACHE_DIR,
                    CACHE_EXPIRE_SECONDS,
                )
                output_bytes = clash.process_yaml_content_clash(
                    yaml_text,
                    template_path,
                    up,
                    down,
                    SHARED_KEYWORDS,
                    SHARED_EXCLUDE_KEYWORDS,
                    clean_node_name,
                )

                # 仅在指定的模板中插入节点
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
                            ih.lower() for ih in clash.CLASH_INCLUDED_HEADERS
                        }:
                            response.headers[h] = v
                return response
            except Exception as e:
                logger.error(f"Clash [Error]: {e}")
                return str(e), 500

    abort(404)


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")