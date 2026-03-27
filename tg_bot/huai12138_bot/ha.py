import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

ha_url = os.getenv("HA_URL", "http://192.168.1.100:8123")
ha_token = os.getenv("HA_TOKEN", "your_long_lived_token_here")

# Lowercase keys for O(1) case-insensitive lookup
DEVICE_MAP = {
    "livingroom": "switch.zimi_cn_1057102723_dhkg01_on_p_2_1",
    "bedroom": "switch.zimi_cn_1021887790_dhkg01_on_p_2_1",
    "kitchen": "switch.zimi_cn_1054932941_dhkg01_on_p_2_1"
}

ACTION_MAP = {
    "on": "turn_on",
    "off": "turn_off",
    "toggle": "toggle"
}

def control_device(room_name, action="turn_off"):
    """
    Control HA switches via REST API.
    Accepts case-insensitive room names and short actions (on/off/toggle).
    """
    # 1. 映射设备 (防御性编程，找不到返回 False)
    entity_id = DEVICE_MAP.get(room_name.lower())
    if not entity_id:
        return False
        
    # 2. 映射动作 (默认 fallback 到 toggle)
    real_action = ACTION_MAP.get(action.lower(), "toggle")
    
    url = f"{ha_url}/api/services/switch/{real_action}"
    
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
        "User-Agent": "Firefox/142.0"
    }
    
    data = {"entity_id": entity_id}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Connection failed for {entity_id}: {e}")
        return False

if __name__ == "__main__":
    # Test cases
    control_device("bedroom", "ON")