import hashlib
import hmac
import logging
import re
import importlib
from pathlib import Path
from flask import Flask, request, abort

# ================= Config =================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

SOURCE_MAP = {"mitce": BASE_DIR / "mitce", "bajie": BASE_DIR / "bajie"}
CUSTOM_CLASH_NODE = BASE_DIR / "node.yaml"
CUSTOM_SINGBOX_NODE = BASE_DIR / "node.json"
TARGET_GROUPS = ["Google"]
INJECT_TEMPLATES = ["m", "openwrt"]

RENAME_MAP = {"香港": "HK", "美国": "US", "新加坡": "SG", "日本": "JP", "家宽": "ISP"}
SHARED_KEYWORDS = ["US", "HK", "SG", "JP", "Hong Kong", "Singapore", "Japan", "United States", "美国", "香港", "新加坡", "日本"]
SHARED_EXCLUDE_KEYWORDS = ["官网", "流量", "倍率", "剩余", "Australia", "到期", "重置", "HK2-HY2", "HK3-HY2", "HK4-HY2", "HK5-HY2"]

ENABLE_CLASH = True
ENABLE_SINGBOX = True

app = Flask(__name__)

# ================= Utils =================
def read_url_from_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if url := line.strip(): return url
    raise ValueError(f"URL [None]: {path}")

def clean_node_name(name: str) -> str:
    if not name: return name
    for k, v in RENAME_MAP.items(): name = name.replace(k, v)
    name = re.sub(r"[^\x00-\x7F]+", "", name)
    return re.sub(r"\s+", " ", name).strip()

# ================= Routing & Dispatch =================
@app.before_request
def restrict_paths():
    if request.path not in {"/mitce", "/bajie"}: abort(404)
    if not (key := request.args.get("key")): abort(404)
    if not hmac.compare_digest(hashlib.sha256(key.encode("utf-8")).hexdigest(), ACCESS_KEY_SHA256): abort(404)

@app.route("/<source>")
def process_source(source):
    path = SOURCE_MAP.get(source)
    if not path: abort(404)
    
    ua = request.headers.get("User-Agent", "")
    is_force_refresh = "u" in request.args

    try:
        url = read_url_from_file(path)
    except Exception as e:
        return str(e), 500

    if ENABLE_SINGBOX and any(k in ua for k in ["SFA", "sing-box"]):
        sb_module = importlib.import_module("sing-box")
        return sb_module.handle_request(
            source, url, ua, is_force_refresh, CACHE_DIR, CACHE_EXPIRE_SECONDS, 
            SHARED_KEYWORDS, SHARED_EXCLUDE_KEYWORDS, clean_node_name, 
            CUSTOM_SINGBOX_NODE, TARGET_GROUPS, INJECT_TEMPLATES
        )

    if ENABLE_CLASH and ("Clash" in ua or "clash" in ua):
        import clash
        return clash.handle_request(
            source, url, ua, is_force_refresh, CACHE_DIR, CACHE_EXPIRE_SECONDS, 
            SHARED_KEYWORDS, SHARED_EXCLUDE_KEYWORDS, clean_node_name, 
            CUSTOM_CLASH_NODE, TARGET_GROUPS, INJECT_TEMPLATES, BASE_DIR
        )

    abort(404)

if __name__ == "__main__":
    app.run(port=5000, host="0.0.0.0")