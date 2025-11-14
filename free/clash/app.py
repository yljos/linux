from flask import Flask, send_file, after_this_request, request
from ruamel.yaml import YAML
import requests
from urllib.parse import unquote
import json
import time
import threading
from datetime import datetime, timedelta
from filelock import FileLock
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
import hashlib
import hmac

# 加载.env文件
load_dotenv()

app = Flask(__name__)


def require_env(key: str) -> str:
    """统一读取必填环境变量，缺失或为空则抛出 RuntimeError。"""
    val = os.getenv(key)
    if val is None or val == "":
        raise RuntimeError(
            f"环境变量 {key} 未设置（必填）。请在 .env 或环境中设置 {key}。"
        )
    return val


# 基础配置（全部从环境读取，缺失则报错）
BASE_DIR = Path(require_env("BASE_DIR")).absolute()
OUTPUT_FOLDER = BASE_DIR / require_env("OUTPUT_FOLDER")
TEMPLATE_PATH_PC = BASE_DIR / require_env("TEMPLATE_PATH_pc")
TEMPLATE_PATH_M = BASE_DIR / require_env("TEMPLATE_PATH_shouji")
HEADERS_CACHE_PATH = OUTPUT_FOLDER / Path(require_env("HEADERS_CACHE_PATH")).name
TEMP_YAML_PATH = OUTPUT_FOLDER / Path(require_env("TEMP_YAML_PATH")).name
TEMP_YAML_LOCK = OUTPUT_FOLDER / Path(require_env("TEMP_YAML_LOCK")).name

USER_AGENT = require_env("USER_AGENT")
CACHE_DURATION = int(require_env("CACHE_DURATION"))
HYSTERIA2_UP = require_env("HYSTERIA2_UP")
HYSTERIA2_DOWN = require_env("HYSTERIA2_DOWN")
HYSTERIA2_UP_M = require_env("HYSTERIA2_UP_M")
HYSTERIA2_DOWN_M = require_env("HYSTERIA2_DOWN_M")
INCLUDED_HEADERS = set(require_env("INCLUDED_HEADERS").split(","))

# 节点替换功能开关（必填，填 true/false）
ENABLE_NODE_REPLACEMENT = require_env("ENABLE_NODE_REPLACEMENT").lower() == "true"

# 从 .env 中读取 client-fingerprint（必填）
CLIENT_FINGERPRINT = require_env("CLIENT_FINGERPRINT")

# 从 .env 读取两个不同的上游 URL 文件路径（必填，文件为无扩展名的文本文件）
MITCE_URL_FILE = (BASE_DIR / require_env("MITCE_URL_FILE")).absolute()
BAJIE_URL_FILE = (BASE_DIR / require_env("BAJIE_URL_FILE")).absolute()
ACCESS_KEY_SHA256 = require_env("ACCESS_KEY_SHA256")  # 共享密钥的 SHA256 十六进制字符串

# 确保输出目录存在
OUTPUT_FOLDER.mkdir(exist_ok=True)

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


def convert_proxies_to_inline(proxies):
    """将proxies列表转换为单行 {} 格式的字符串"""
    inline_proxies = []
    for proxy in proxies:
        # 构建单行的字典格式
        items = []
        for key, value in proxy.items():
            # 需要用引号的键名（如果包含特殊字符）
            key_str = f'"{key}"' if "-" in key else key

            if isinstance(value, bool):
                # 布尔值必须最先检查（因为bool是int的子类）
                items.append(f"{key_str}: {str(value).lower()}")
            elif isinstance(value, str):
                # 字符串值用引号
                items.append(f"{key_str}: {repr(value)}")
            elif isinstance(value, (int, float)):
                items.append(f"{key_str}: {value}")
            elif isinstance(value, dict):
                # 嵌套字典也转为单行格式
                nested_items = []
                for k, v in value.items():
                    k_str = f'"{k}"' if "-" in k else k
                    if isinstance(v, bool):
                        # 嵌套字典中的布尔值也保持小写
                        nested_items.append(f"{k_str}: {str(v).lower()}")
                    elif isinstance(v, str):
                        nested_items.append(f"{k_str}: {repr(v)}")
                    else:
                        nested_items.append(f"{k_str}: {v}")
                items.append(f"{key_str}: {{{', '.join(nested_items)}}}")
            elif isinstance(value, list):
                # 列表转为 [item1, item2] 格式
                items.append(f"{key_str}: {value}")
            else:
                # 其他类型，直接转为字符串
                items.append(f"{key_str}: {repr(value)}")
        inline_proxies.append("  - {" + ", ".join(items) + "}")
    return "\n".join(inline_proxies)


yaml = setup_yaml_config()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_headers_cache(url, headers):
    """保存请求头缓存，仅保存白名单中的header"""
    try:
        if HEADERS_CACHE_PATH.exists():
            with open(HEADERS_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
        else:
            cache = {}

        filtered_headers = {
            k: v
            for k, v in headers.items()
            if k.lower() in {h.lower() for h in INCLUDED_HEADERS}
        }

        cache[url] = {
            "headers": filtered_headers,
            "timestamp": datetime.now().isoformat(),
        }

        with open(HEADERS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存headers缓存失败: {e}")


def get_headers_cache(url):
    """获取指定URL的headers缓存，检查是否过期"""
    try:
        if HEADERS_CACHE_PATH.exists():
            with open(HEADERS_CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if url in cache:
                    cache_time = datetime.fromisoformat(cache[url]["timestamp"])
                    if datetime.now() - cache_time < timedelta(seconds=CACHE_DURATION):
                        return cache[url]["headers"]
    except Exception as e:
        logger.error(f"读取headers缓存失败: {e}")
    return None


def fetch_yaml(url):
    """获取 YAML 内容并缓存到本地"""
    temp_path = TEMP_YAML_PATH.with_suffix(".tmp")

    with FileLock(TEMP_YAML_LOCK):
        try:
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            save_headers_cache(url, response.headers)

            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            if not temp_path.exists() or os.path.getsize(temp_path) == 0:
                raise IOError("临时文件写入失败")

            if TEMP_YAML_PATH.exists():
                TEMP_YAML_PATH.unlink()
            temp_path.rename(TEMP_YAML_PATH)

            logger.info(f"成功缓存YAML文件: {url}")
            return TEMP_YAML_PATH

        except Exception as e:
            logger.error(f"获取YAML失败: {str(e)}")
            if temp_path.exists():
                temp_path.unlink()
            raise


def save_node_names(proxies):
    """提取节点名称并保存到nodes.yaml文件"""
    try:
        # 提取所有代理节点的名称
        node_names = []
        for proxy in proxies:
            if isinstance(proxy, dict) and "name" in proxy:
                node_names.append(proxy["name"])

        # 准备要保存的数据结构
        nodes_data = {
            "node_names": node_names,
            "total": len(node_names),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 配置YAML输出格式
        nodes_yaml = setup_yaml_config()

        # 保存到nodes.yaml
        nodes_path = OUTPUT_FOLDER / "nodes.yaml"
        with open(nodes_path, "w", encoding="utf-8") as f:
            nodes_yaml.dump(nodes_data, f)

        logger.info(f"成功保存节点名称到 {nodes_path}, 共 {len(node_names)} 个节点")
        return nodes_path
    except Exception as e:
        logger.error(f"保存节点名称失败: {str(e)}")
        return None


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


def replace_proxy_groups_with_nodes(template_data):
    """将代理组中的fallback节点替换为实际节点"""
    try:
        # 检查nodes.yaml是否存在
        nodes_path = OUTPUT_FOLDER / "nodes.yaml"
        if not nodes_path.exists():
            logger.warning("nodes.yaml不存在，无法替换节点")
            return template_data

        # 读取nodes.yaml获取所有节点名称
        nodes_yaml = setup_yaml_config()
        with open(nodes_path, "r", encoding="utf-8") as f:
            nodes_data = nodes_yaml.load(f)

        # 获取节点名称列表
        node_names = nodes_data.get("node_names", [])
        if not node_names:
            logger.warning("nodes.yaml中未找到节点名称")
            return template_data

        # 定义区域配置
        region_configs = {
            "US_fallback": (["US", "美国"], "US"),
            "HK_fallback": (["HK", "香港"], "HK"),
            "SG_fallback": (["SG", "新加坡", "Singapore"], "SG"),
            "JP_fallback": (["JP", "日本", "Japan"], "JP"),
            "TW_fallback": (["TW", "台湾", "Taiwan"], "TW"),
        }

        # 筛选各区域节点
        region_nodes = {}
        for fallback_key, (patterns, _) in region_configs.items():
            region_nodes[fallback_key] = filter_nodes_by_region(node_names, patterns)
            logger.info(
                f"找到 {len(region_nodes[fallback_key])} 个{fallback_key.replace('_fallback', '')}节点"
            )

        # 处理代理组
        proxy_groups = template_data.get("proxy-groups", [])
        for group in proxy_groups:
            if (
                isinstance(group, dict)
                and group.get("type") == "fallback"
                and "proxies" in group
            ):
                group_name = group.get("name", "未命名")
                proxies = group["proxies"]

                # 替换所有区域的fallback节点
                for fallback_name, nodes in region_nodes.items():
                    replace_fallback_nodes_in_group(
                        proxies, fallback_name, nodes, group_name
                    )

        return template_data
    except Exception as e:
        logger.error(f"替换代理组节点失败: {str(e)}")
        return template_data


def process_yaml_content(yaml_path, template_path: Path, up_pref: str, down_pref: str):
    """处理本地YAML文件"""
    try:
        # 读取标准模板（获取原始顺序）
        with open(template_path, "r", encoding="utf-8") as f:
            template_text = f.read()

        # 解析YAML获取数据结构
        with open(yaml_path, "r", encoding="utf-8") as f:
            input_data = yaml.load(f)

        if not isinstance(input_data, dict):
            raise ValueError("YAML内容必须是有效的字典格式")

        # 读取标准模板
        with open(template_path, "r", encoding="utf-8") as f:
            template_data = yaml.load(f)

        proxies = input_data.get("proxies", [])
        if not proxies:
            raise ValueError("YAML文件中未找到有效的proxies配置")

        # 处理代理配置
        for proxy in proxies:
            process_proxy_config(proxy, up_pref, down_pref)

        # 提取节点名称并保存（如果启用了节点替换功能）
        if ENABLE_NODE_REPLACEMENT:
            save_node_names(proxies)

        # 替换代理组中的节点（如果启用了节点替换功能）
        if ENABLE_NODE_REPLACEMENT:
            template_data = replace_proxy_groups_with_nodes(template_data)

        # 保存处理后的YAML（只修改proxies部分为单行格式）
        output_path = OUTPUT_FOLDER / "config.yaml"
        with open(output_path, "w", encoding="utf-8") as f:
            import re

            # 生成新的proxies内容
            proxies_inline = convert_proxies_to_inline(proxies)

            # 使用正则表达式替换模板中的 proxies: [] 部分
            # 精确匹配 "proxies: []" 这一行
            pattern = r"proxies:\s*\[\s*\]"

            if re.search(pattern, template_text):
                # 找到了 proxies: []，替换它
                replacement = "proxies:\n" + proxies_inline
                result = re.sub(pattern, replacement, template_text)
                f.write(result)
            else:
                # 如果没找到proxies部分，直接输出模板并追加proxies
                f.write(template_text)
                if not template_text.endswith("\n"):
                    f.write("\n")
                f.write("proxies:\n")
                f.write(proxies_inline)
                f.write("\n")

        return output_path

    except Exception as e:
        logger.error(f"处理YAML内容失败: {str(e)}")
        raise


def cleanup_files(*paths):
    """清理指定的文件"""
    for path in paths:
        try:
            if isinstance(path, (str, Path)) and Path(path).exists():
                Path(path).unlink()
                logger.info(f"成功删除文件: {path}")
            elif isinstance(path, (str, Path)):
                logger.warning(f"文件不存在，跳过删除: {path}")
        except Exception as e:
            logger.error(f"清理文件失败 {path}: {str(e)}")


def cleanup_response(response, temp_yaml_path, output_path):
    """处理响应后的清理函数"""

    def delayed_cleanup():
        logger.info("开始执行延迟清理...")
        time.sleep(30)  # 等待30秒后删除文件
        logger.info("30秒等待结束，开始清理文件")
        cleanup_files(temp_yaml_path, output_path, HEADERS_CACHE_PATH)
        logger.info("文件清理完成")

    # 在后台线程中执行清理
    threading.Thread(target=delayed_cleanup, daemon=True).start()
    return response


@app.route("/mitce")
def process_mitce():
    temp_yaml_path = None
    output_path = None

    try:
        yaml_url = unquote(read_url_from_file(MITCE_URL_FILE))
        # 模板选择：默认 pc，?config=m 使用手机模板
        config_val = (request.args.get("config", "pc") or "pc").lower()
        template_path = TEMPLATE_PATH_M if config_val == "m" else TEMPLATE_PATH_PC
        # 根据模板选择带宽参数
        up_pref = HYSTERIA2_UP_M if config_val == "m" else HYSTERIA2_UP
        down_pref = HYSTERIA2_DOWN_M if config_val == "m" else HYSTERIA2_DOWN

        logger.info(f"处理URL(/mitce): {yaml_url} 使用模板: {template_path}")

        temp_yaml_path = fetch_yaml(yaml_url)
        output_path = process_yaml_content(
            temp_yaml_path, template_path, up_pref, down_pref
        )
        cached_headers = get_headers_cache(yaml_url)

        response = send_file(
            output_path,
            mimetype="application/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )

        response.headers["Content-Type"] = "application/yaml; charset=utf-8"

        if cached_headers:
            for header, value in cached_headers.items():
                if header.lower() in {h.lower() for h in INCLUDED_HEADERS}:
                    response.headers[header] = value

        # 修复：将清理函数定义在外部，通过闭包捕获必要的变量
        temp_path = temp_yaml_path
        out_path = output_path

        @after_this_request
        def cleanup(resp):  # <-- 修改此处：将 'response' 重命名为 'resp' 以避免命名冲突
            """注册一个函数，在请求处理完毕后执行清理操作。"""
            return cleanup_response(resp, temp_path, out_path)

        return response

    except Exception as e:
        if temp_yaml_path or output_path:
            cleanup_files(temp_yaml_path, output_path)  # 清理临时文件和输出文件
        logger.error(f"处理请求失败: {str(e)}")
        return str(e), 500


@app.route("/bajie")
def process_bajie():
    temp_yaml_path = None
    output_path = None

    try:
        yaml_url = unquote(read_url_from_file(BAJIE_URL_FILE))
        # 模板选择：默认 pc，?config=m 使用手机模板
        config_val = (request.args.get("config", "pc") or "pc").lower()
        template_path = TEMPLATE_PATH_M if config_val == "m" else TEMPLATE_PATH_PC
        up_pref = HYSTERIA2_UP_M if config_val == "m" else HYSTERIA2_UP
        down_pref = HYSTERIA2_DOWN_M if config_val == "m" else HYSTERIA2_DOWN
        logger.info(f"处理URL(/bajie): {yaml_url} 使用模板: {template_path}")

        temp_yaml_path = fetch_yaml(yaml_url)
        output_path = process_yaml_content(
            temp_yaml_path, template_path, up_pref, down_pref
        )
        cached_headers = get_headers_cache(yaml_url)

        response = send_file(
            output_path,
            mimetype="application/yaml",
            as_attachment=True,
            download_name="config.yaml",
        )

        response.headers["Content-Type"] = "application/yaml; charset=utf-8"

        if cached_headers:
            for header, value in cached_headers.items():
                if header.lower() in {h.lower() for h in INCLUDED_HEADERS}:
                    response.headers[header] = value

        temp_path = temp_yaml_path
        out_path = output_path

        @after_this_request
        def cleanup(resp):
            return cleanup_response(resp, temp_path, out_path)

        return response

    except Exception as e:
        if temp_yaml_path or output_path:
            cleanup_files(temp_yaml_path, output_path)
        logger.error(f"处理请求失败(/bajie): {str(e)}")
        return str(e), 500


if __name__ == "__main__":
    # DEBUG, PORT, HOST 也为必填环境变量（缺失将抛错）
    debug_mode = require_env("DEBUG").lower() in ("true", "1", "yes")
    port = int(require_env("PORT"))
    host = require_env("HOST")

    app.run(debug=debug_mode, port=port, host=host)
