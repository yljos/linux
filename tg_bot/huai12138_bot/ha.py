import httpx
import os
from dotenv import load_dotenv

load_dotenv()

ha_url = os.getenv("HA_URL", "https://your-ha-domain.com")
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

def control_device(room_name, action="toggle"):
    """
    Control HA switches via REST API using httpx.
    Accepts case-insensitive room names and short actions (on/off/toggle).
    """
    entity_id = DEVICE_MAP.get(room_name.lower())
    if not entity_id:
        return False
        
    real_action = ACTION_MAP.get(action.lower(), "toggle")
    url = f"{ha_url}/api/services/switch/{real_action}"
    
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
        "User-Agent": "Firefox/142.0"
    }
    
    data = {"entity_id": entity_id}

    try:
        # Standard HTTPS request, automatically verifies valid SSL certificates
        httpx.post(url, headers=headers, json=data, timeout=10.0)
    except Exception as e:
        print(f"Connection failed for {entity_id}: {e}")
        return False

if __name__ == "__main__":
    control_device("LivingRoom", "on")