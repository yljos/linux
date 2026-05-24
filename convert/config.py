import logging
from pathlib import Path

# ================= Logging =================
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)

# ================= Auth & General Config =================
ACCESS_KEY_SHA256 = "51ef50ce29aa4cf089b9b076cb06e30445090b323f0882f1251c18a06fc228ed"
BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_EXPIRE_SECONDS = 86400

SOURCE_MAP = {
    "mitce": BASE_DIR / "mitce",
    "bajie": BASE_DIR / "bajie",
}

# ================= Custom Node Config =================
CUSTOM_CLASH_NODE = BASE_DIR / "node.yaml"
CUSTOM_SINGBOX_NODE = BASE_DIR / "node.json"
TARGET_GROUPS = ["Google"]
INJECT_TEMPLATES = ["m", "openwrt"]

# ================= Keywords & Rename Maps =================
RENAME_MAP = {
    "香港": "HK", "美国": "US", "新加坡": "SG", "日本": "JP", "家宽": "ISP",
}

SHARED_KEYWORDS = [
    "US", "HK", "SG", "JP", "Hong Kong", "Singapore", "Japan", "United States",
    "美国", "香港", "新加坡", "日本",
]

SHARED_EXCLUDE_KEYWORDS = [
    "官网", "流量", "倍率", "剩余", "Australia", "到期", "重置",
    "HK2-HY2", "HK3-HY2", "HK4-HY2", "HK5-HY2",
]

# ================= Sing-box Config =================
SB_TEMPLATE_MAP = {
    "openwrt": "json/openwrt.json",
    "pc": "json/pc.json",
    "mtun": "json/mtun.json",
    "m": "json/m.json",
}

# ================= Clash Config =================
CLASH_TEMPLATE_PC = BASE_DIR / "yaml/pc.yaml"
CLASH_TEMPLATE_MTUN = BASE_DIR / "yaml/mtun.yaml"
CLASH_TEMPLATE_OPENWRT = BASE_DIR / "yaml/openwrt.yaml"
CLASH_TEMPLATE_M = BASE_DIR / "yaml/m.yaml"

CLASH_USER_AGENT = "clash-verge"
CLASH_INCLUDED_HEADERS = ["Subscription-Userinfo"]
CLASH_HY2_UP = "50 Mbps"
CLASH_HY2_DOWN = "200 Mbps"
CLASH_HY2_UP_M = "30 Mbps"
CLASH_HY2_DOWN_M = "60 Mbps"
CLASH_FINGERPRINT = "firefox"