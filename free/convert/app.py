import hashlib
import hmac
import io
import logging
import re
from pathlib import Path
from urllib.parse import unquote
from flask import Flask, send_file, request, abort, Response, jsonify

import clash
import singbox

app = Flask(__name__)

# ================= 鉴权与通用配置 =================
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

MITCE_URL_FILE = Path("mitce").absolute()
BAJIE_URL_FILE = Path("bajie").absolute()
source_map = {
    "mitce": MITCE_URL_FILE,
    "bajie": BAJIE_URL_FILE,
}

# ================= [合并] 关键词与黑名单 =================
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

    # 1. 优先检查 Sing-box 客户端
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
                return Response(
                    json_str,
                    mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=config.json"},
                )
            except FileNotFoundError as e:
                return jsonify({"error": str(e)}), 500
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except RuntimeError as e:
                return jsonify({"error": str(e)}), 500
            except Exception as e:
                logger.error(f"Singbox 处理内部错误: {e}")
                return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500

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
        "m": (clash.CLASH_TEMPLATE_M, clash.CLASH_HY2_UP_M, clash.CLASH_HY2_DOWN_M),
        "mtun": (
            clash.CLASH_TEMPLATE_MTUN,
            clash.CLASH_HY2_UP_M,
            clash.CLASH_HY2_DOWN_M,
        ),
        "pc": (clash.CLASH_TEMPLATE_PC, clash.CLASH_HY2_UP, clash.CLASH_HY2_DOWN),
        "openwrt": (
            clash.CLASH_TEMPLATE_OPENWRT,
            clash.CLASH_HY2_UP,
            clash.CLASH_HY2_DOWN,
        ),
    }

    template_path, up, down = config_map[config_val]
    logger.info(
        f"[Clash] | [Template: {config_val}] | [Force update: {is_force_refresh}] | [UA: {ua}]"
    )

    try:
        url = read_url_from_file(path)
        yaml_text, headers_data = clash.fetch_yaml_text_clash(
            unquote(url), source, is_force_refresh, CACHE_DIR, CACHE_EXPIRE_SECONDS
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

        response = send_file(
            io.BytesIO(output_bytes),
            mimetype="text/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )
        if headers_data:
            for h, v in headers_data.items():
                if h.lower() in {ih.lower() for ih in clash.CLASH_INCLUDED_HEADERS}:
                    response.headers[h] = v
        return response
    except Exception as e:
        logger.error(f"Clash [Error]: {e}")
        return str(e), 500


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")
