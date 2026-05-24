from typing import Any, Dict, Union, List, Tuple
from config import CLASH_FINGERPRINT


# ================= Sing-box Parsers =================
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

    # Core fix: normalize port range symbols between Clash and Sing-box
    if "ports" in proxy:
        node["server_ports"] = str(proxy["ports"]).replace("-", ":")
    elif "port" in proxy:
        port_val = str(proxy["port"])
        if "-" in port_val:
            node["server_ports"] = port_val.replace("-", ":")
        else:
            node["server_port"] = int(proxy["port"])

    node["up_mbps"] = 50
    node["down_mbps"] = 200
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
    return None


# ================= Clash Parsers =================
def is_valid_clash_yaml(text: str) -> bool:
    return bool(text and "proxies:" in text)


def filter_node_names_clash(
    proxies: List[Any], shared_kw: List[str], shared_ex_kw: List[str]
) -> Tuple[List[str], List[str]]:
    all_names = [
        str(p.get("name"))
        for p in proxies
        if isinstance(p, dict) and isinstance(p.get("name"), str)
    ]
    valid_kw = [str(kw).lower() for kw in shared_kw if isinstance(kw, str)]
    valid_ex_kw = [str(ex).lower() for ex in shared_ex_kw if isinstance(ex, str)]

    filtered = [
        n
        for n in all_names
        if any(kw in n.lower() for kw in valid_kw)
        and not any(ex in n.lower() for ex in valid_ex_kw)
    ]
    return filtered, all_names


def process_proxy_config_clash(proxy: Dict[str, Any], up_pref: str, down_pref: str):
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
