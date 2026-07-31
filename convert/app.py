import hashlib
import hmac
import io
import logging
from urllib.parse import unquote
from flask import Flask, send_file, request, abort, Response, jsonify

from config import (
    ACCESS_KEY_SHA256,
    CACHE_DIR,
    CACHE_EXPIRE_SECONDS,
    SOURCE_MAP,
    INJECT_TEMPLATES,
    TARGET_GROUPS,
    CUSTOM_CLASH_NODE,
    CUSTOM_SINGBOX_NODE,
    SHARED_KEYWORDS,
    SHARED_EXCLUDE_KEYWORDS,
    CLASH_TEMPLATE_M,
    CLASH_TEMPLATE_MTUN,
    CLASH_TEMPLATE_PC,
    CLASH_TEMPLATE_OPENWRT,
    CLASH_HY2_UP_M,
    CLASH_HY2_DOWN_M,
    CLASH_HY2_UP,
    CLASH_HY2_DOWN,
    CLASH_INCLUDED_HEADERS,
)
from utils import (
    read_url_from_file,
    clean_node_name,
    inject_custom_clash_node,
    inject_custom_singbox_node,
)

# ================= Module Switches =================
ENABLE_CLASH = True
ENABLE_SINGBOX = False

app = Flask(__name__)
logger = logging.getLogger(__name__)


# ================= Routing Protection & Dispatch =================
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
    path = SOURCE_MAP.get(source)
    if not path:
        abort(404)

    ua = request.headers.get("User-Agent", "")
    is_force_refresh = "u" in request.args

    # --- 1. Sing-box Dispatch Logic ---
    if ENABLE_SINGBOX:
        # Import dynamically when ENABLE_SINGBOX is True
        from core_singbox import fetch_and_process_singbox

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
                    json_str = fetch_and_process_singbox(
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
                    logger.error(f"Singbox internal error: {e}")
                    return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

    # --- 2. Clash Dispatch Logic ---
    if ENABLE_CLASH:
        # Import dynamically when ENABLE_CLASH is True
        from core_clash import fetch_yaml_text_clash, process_yaml_content_clash

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
                "m": (CLASH_TEMPLATE_M, CLASH_HY2_UP_M, CLASH_HY2_DOWN_M),
                "mtun": (CLASH_TEMPLATE_MTUN, CLASH_HY2_UP_M, CLASH_HY2_DOWN_M),
                "pc": (CLASH_TEMPLATE_PC, CLASH_HY2_UP, CLASH_HY2_DOWN),
                "openwrt": (CLASH_TEMPLATE_OPENWRT, CLASH_HY2_UP, CLASH_HY2_DOWN),
            }
            template_path, up, down = config_map[clash_config_val]
            logger.info(
                f"[Clash] | [Template: {clash_config_val}] | [Force: {is_force_refresh}] | [UA: {ua}]"
            )

            try:
                url = read_url_from_file(path)
                yaml_text, headers_data = fetch_yaml_text_clash(
                    unquote(url),
                    source,
                    is_force_refresh,
                    CACHE_DIR,
                    CACHE_EXPIRE_SECONDS,
                )
                output_bytes = process_yaml_content_clash(
                    yaml_text,
                    template_path,
                    up,
                    down,
                    SHARED_KEYWORDS,
                    SHARED_EXCLUDE_KEYWORDS,
                    clean_node_name,
                )

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
                        if h.lower() in {ih.lower() for ih in CLASH_INCLUDED_HEADERS}:
                            response.headers[h] = v
                return response
            except Exception as e:
                logger.error(f"Clash [Error]: {e}")
                return str(e), 500

    abort(404)


if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")