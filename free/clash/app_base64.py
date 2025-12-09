"""
Flask应用 - 纯内存处理订阅节点信息，生成config.yaml
支持从URL参数获取base64编码数据，解码后处理vless://、ss://、hysteria2://、trojan://节点信息
"""

from flask import Flask, request, jsonify, send_file
import base64
import os
import requests
import io  # 导入内存I/O模块
from ruamel.yaml import YAML

# 导入现有的转换器模块
try:
    from vless import parse_vless_url
except ImportError:
    print("警告: 无法导入vless_converter模块")
    parse_vless_url = None
try:
    from ss import parse_shadowsocks_url as parse_ss_url
except ImportError:
    print("警告: 无法导入ss_converter模块")
    parse_ss_url = None
try:
    from hy2 import parse_hysteria2_url
except ImportError:
    print("警告: 无法导入hysteria2_converter模块")
    parse_hysteria2_url = None
try:
    from trojan import parse_trojan_url
except ImportError:
    print("警告: 无法导入trojan_converter模块")
    parse_trojan_url = None


app = Flask(__name__)

# --- 预加载 b.yaml 内容到内存 (假设 b.yaml 存在于同一目录) ---
# 建议：将 b.yaml 文件的内容定义为一个全局常量 BASE_YAML_CONTENT
BASE_YAML_CONTENT = ""
try:
    b_yaml_path = os.path.join(os.path.dirname(__file__), "b.yaml")
    with open(b_yaml_path, "r", encoding="utf-8") as f:
        BASE_YAML_CONTENT = f.read()
    print("b.yaml 已成功预加载到内存。")
except FileNotFoundError:
    print("警告: b.yaml 文件未找到，将使用空基础配置。")
    BASE_YAML_CONTENT = "{}"
except Exception as e:
    print(f"警告: 加载b.yaml时发生错误: {e}，将使用空基础配置。")
    BASE_YAML_CONTENT = "{}"
# -------------------------------------------------------------------


def decode_base64_content(content):
    """解码base64内容"""
    try:
        content = content.replace("-", "+").replace("_", "/")
        padding = len(content) % 4
        if padding:
            content += "=" * (4 - padding)
        decoded_bytes = base64.b64decode(content)
        return decoded_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Base64解码失败: {str(e)}")


# (fetch_subscription_info 和 fetch_content_from_url 保持不变...)
def fetch_subscription_info(url):
    """使用clash verge User-Agent获取订阅信息"""
    try:
        headers = {"User-Agent": "clash-verge"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.headers.get("Subscription-Userinfo", "")
    except Exception as e:
        print(f"获取订阅信息失败: {str(e)}")
        return ""


def fetch_content_from_url(url):
    """从URL获取base64编码的内容并解码"""
    try:
        subscription_userinfo = ""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text.strip()
        decoded_content = decode_base64_content(content)
        return decoded_content, subscription_userinfo
    except Exception as e:
        raise ValueError(f"获取URL内容失败: {str(e)}")


def extract_urls_from_text(text):
    """从文本中提取所有节点URL"""
    urls = []
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith(
            ("vless://", "ss://", "hysteria2://", "hy2://", "trojan://")
        ):
            urls.append(line)
    return urls


def parse_node_url(url):
    """根据协议类型解析节点URL"""
    url = url.strip()
    if url.startswith("vless://"):
        if parse_vless_url:
            return parse_vless_url(url)
        else:
            raise ValueError("VLESS转换器未可用")
    elif url.startswith("ss://"):
        if parse_ss_url:
            return parse_ss_url(url)
        else:
            raise ValueError("SS转换器未可用")
    elif url.startswith(("hysteria2://", "hy2://")):
        if parse_hysteria2_url:
            return parse_hysteria2_url(url)
        else:
            raise ValueError("Hysteria2转换器未可用")
    elif url.startswith("trojan://"):
        if parse_trojan_url:
            return parse_trojan_url(url)
        else:
            raise ValueError("Trojan转换器未可用")
    else:
        raise ValueError(f"不支持的协议类型: {url[:20]}...")


@app.route("/", methods=["GET"])
def index():
    return "", 200


@app.route("/<path:url_path>", methods=["GET"])
def process_nodes_from_path(url_path):
    """通过路径参数处理节点信息并生成config.yaml"""
    full_url = url_path
    if request.query_string:
        query_part = request.query_string.decode("utf-8")
        full_url = f"{url_path}?{query_part}"

    try:
        decoded_content, subscription_userinfo = fetch_content_from_url(full_url)
        node_urls = extract_urls_from_text(decoded_content)

        if not node_urls:
            return (
                jsonify(
                    {
                        "error": "未找到有效的节点URL",
                        "url": full_url,
                    }
                ),
                400,
            )

        # 解析所有节点
        nodes, errors = [], []
        for idx, url in enumerate(node_urls):
            try:
                node_config = parse_node_url(url)
                nodes.append(node_config)
            except Exception as e:
                errors.append(f"节点 {idx + 1} 解析失败: {str(e)}")

        if not nodes:
            return (
                jsonify(
                    {"error": "所有节点解析都失败了", "errors": errors, "url": full_url}
                ),
                400,
            )

        # --- 纯内存 YAML 处理开始 ---
        yaml_ruamel = YAML()
        yaml_ruamel.preserve_quotes = True

        # 1. 从内存常量加载基础配置
        base_config = yaml_ruamel.load(BASE_YAML_CONTENT)

        proxies = list(base_config.get("proxies", []))
        proxies.extend(nodes)

        from ruamel.yaml.comments import CommentedSeq, CommentedMap

        def dict_to_flow_map(d):
            if not isinstance(d, dict):
                return d
            m = CommentedMap()
            for k, v in d.items():
                if isinstance(v, bool):
                    m[k] = v
                elif isinstance(v, dict):
                    m[k] = dict_to_flow_map(v)
                elif isinstance(v, list):
                    m[k] = CommentedSeq(
                        [dict_to_flow_map(i) if isinstance(i, dict) else i for i in v]
                    )
                    m[k].fa.set_flow_style()
                else:
                    m[k] = v
            m.fa.set_flow_style()
            return m

        proxies_flow = [
            dict_to_flow_map(p) if isinstance(p, dict) else p for p in proxies
        ]
        base_config["proxies"] = CommentedSeq(proxies_flow)

        # 2. 写入内存缓冲区
        output_stream = io.StringIO()
        yaml_ruamel.width = 4096
        yaml_ruamel.dump(base_config, output_stream)

        # 3. 将 StringIO 内容作为文件发送
        output_stream.seek(0)

        # 使用 io.BytesIO 包装，以便 send_file 可以正确处理 MIME 类型和附件
        # 也可以直接返回 output_stream.getvalue()，但使用 send_file 兼容性更好
        return_data = io.BytesIO(output_stream.getvalue().encode("utf-8"))

        response = send_file(
            return_data,
            mimetype="text/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )
        # --- 纯内存 YAML 处理结束 ---

        if subscription_userinfo:
            response.headers["Subscription-Userinfo"] = subscription_userinfo
        return response

    except Exception as e:
        # 在生产环境中，应该记录完整的 traceback
        return jsonify({"error": f"处理过程中发生错误: {str(e)}", "url": full_url}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
