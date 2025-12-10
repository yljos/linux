"""
Flask应用 - 处理base64编码的节点信息，生成config.json
支持从URL参数获取base64编码数据，并将其节点注入到JSON模板中。
"""

import base64
import requests
import json
import re
import os
import sys
import hashlib
from typing import Any, Dict, List, Tuple, Union
from flask import Flask, request, jsonify, Response
from vless_converter import parse_vless_url
from ss_converter import parse_shadowsocks_url as parse_ss_url
from hysteria2_converter import parse_hysteria2_url


# ===== 可修改配置项 =====

NODE_REGION_KEYWORDS = ["JP", "SG", "HK", "US", "美国", "香港", "新加坡", "日本"]
NODE_EXCLUDE_KEYWORDS = ["到期", "官网", "剩余", "10"]
CONFIG_TEMPLATE_FILENAME = "1.12.json"
# 密码哈希和API地址文件
MITCE_PASSWORD_HASH = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
MITCE_API_FILE = "mitce"  # 当前目录下的 mitce 文件
BAJIE_API_FILE = "bajie"  # 当前目录下的 bajie 文件

app = Flask(__name__)


# 支持 /nodes/<source> 和 /<source> 两种路由
@app.route("/nodes/<source>", methods=["GET"])
@app.route("/<source>", methods=["GET"])
def process_nodes_from_source(source: str) -> Union[Response, Tuple[Response, int]]:
    key = request.args.get("key", "")
    if not key:
        return jsonify({"error": "需要鉴权"}), 401

    # 鉴权
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
    if key_hash != MITCE_PASSWORD_HASH:
        return jsonify({"error": "鉴权失败"}), 401

    # 选择文件
    if source == "mitce":
        api_file = MITCE_API_FILE
    elif source == "bajie":
        api_file = BAJIE_API_FILE
    else:
        return jsonify({"error": "不支持的参数"}), 400

    # 读取文件内容作为 base64 链接
    file_path = os.path.join(os.path.dirname(__file__), api_file)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            url = f.read().strip()
            if not url:
                raise ValueError(f"{source} 文件内容为空")
    except Exception as e:
        return jsonify({"error": f"读取 {source} 文件失败: {str(e)}"}), 500

    try:
        decoded_content, _ = fetch_content_from_url(url)
        node_urls = extract_urls_from_text(decoded_content)
        if not node_urls:
            return (
                jsonify(
                    {
                        "error": "未找到有效的节点URL",
                        "decoded_content": (
                            decoded_content[:500] + "..."
                            if len(decoded_content) > 500
                            else decoded_content
                        ),
                        "source": source,
                    }
                ),
                400,
            )

        nodes, errors = [], []
        for i, node_url in enumerate(node_urls):
            try:
                node_config = parse_node_url(node_url)
                if "name" in node_config and "tag" not in node_config:
                    node_config["tag"] = node_config["name"]
                nodes.append(node_config)
            except Exception as e:
                errors.append(f"节点 {i + 1} 解析失败: {str(e)}")

        if not nodes:
            return (
                jsonify(
                    {
                        "error": "所有节点解析都失败了",
                        "errors": errors,
                        "source": source,
                    }
                ),
                400,
            )

        config_path = os.path.join(os.path.dirname(__file__), CONFIG_TEMPLATE_FILENAME)
        with open(config_path, "r", encoding="utf-8") as f:
            base_config = json.load(f)

        outbounds = base_config.get("outbounds", [])
        existing_tags = {o.get("tag") for o in outbounds}
        new_nodes = [
            n for n in nodes if n.get("tag") and n.get("tag") not in existing_tags
        ]
        outbounds.extend(new_nodes)

        def node_tag_valid(tag: str) -> bool:
            tag_upper = tag.upper() if tag else ""
            if not any(region.upper() in tag_upper for region in NODE_REGION_KEYWORDS):
                return False
            if any(exclude in tag for exclude in NODE_EXCLUDE_KEYWORDS):
                return False
            return True

        filtered_outbounds = [
            o
            for o in outbounds
            if node_tag_valid(o.get("tag", ""))
            or o.get("type") in ["urltest", "selector", "direct", "block"]
        ]

        for outbound in filtered_outbounds:
            if outbound.get("type") == "urltest" and "filter" in outbound:
                regex_list = [
                    reg
                    for f in outbound.get("filter", [])
                    for reg in f.get("regex", [])
                ]
                if not regex_list:
                    del outbound["filter"]
                    continue

                pattern = "|".join(regex_list)
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    all_node_tags = [
                        o.get("tag")
                        for o in filtered_outbounds
                        if o.get("tag")
                        and o.get("type")
                        not in ["urltest", "selector", "direct", "block"]
                    ]
                    matched_tags = [
                        tag for tag in all_node_tags if compiled.search(tag)
                    ]
                    if matched_tags:
                        outbound["outbounds"] = matched_tags
                    else:
                        outbound["outbounds"] = ["D"]
                except re.error as e:
                    print(f"无效的正则表达式 '{pattern}': {e}", file=sys.stderr)
                    continue

                del outbound["filter"]

        base_config["outbounds"] = filtered_outbounds

        json_str = json.dumps(base_config, ensure_ascii=False, separators=(",", ":"))
        return Response(
            json_str,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=config.json"},
        )
    except Exception as e:
        return (
            jsonify({"error": f"处理过程中发生错误: {str(e)}", "source": source}),
            500,
        )


def decode_base64_content(content: str) -> str:
    try:
        content = content.replace("-", "+").replace("_", "/")
        padding = len(content) % 4
        if padding:
            content += "=" * (4 - padding)
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")


def fetch_content_from_url(url: str) -> Tuple[str, str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text.strip()
        decoded_content = decode_base64_content(content)
        return decoded_content, ""
    except Exception as e:
        raise ValueError(f"获取URL内容失败: {str(e)}")


def extract_urls_from_text(text: str) -> List[str]:
    urls = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and line.startswith(("vless://", "ss://", "hysteria2://", "hy2://")):
            urls.append(line)
    return urls


def parse_node_url(url: str) -> Dict[str, Any]:
    url = url.strip()
    if url.startswith("vless://"):
        return parse_vless_url(url)
    elif url.startswith("ss://"):
        return parse_ss_url(url)
    elif url.startswith(("hysteria2://", "hy2://")):
        return parse_hysteria2_url(url)
    else:
        raise ValueError(f"不支持的协议类型: {url[:20]}...")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
