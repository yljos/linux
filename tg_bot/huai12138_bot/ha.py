import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

ha_url = os.getenv("HA_URL", "http://192.168.1.100:8123")
ha_token = os.getenv("HA_TOKEN", "your_long_lived_token_here")

# Reversed map for direct O(1) lookup
DEVICE_MAP = {
    "LivingRoom": "switch.zimi_cn_1057102723_dhkg01_on_p_2_1",
    "BedRoom": "switch.zimi_cn_1021887790_dhkg01_on_p_2_1",
    "Kitchen": "switch.zimi_cn_1054932941_dhkg01_on_p_2_1"
}

def control_device(room_name, action="turn_off"):
    """
    Control HA switches via REST API by room name.
    Common actions: turn_on, turn_off, toggle
    """
    # Direct lookup, no need for loops or conditions
    entity_id = DEVICE_MAP[room_name]
    
    # Hardcoded to 'switch' domain
    url = f"{ha_url}/api/services/switch/{action}"
    
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
        "User-Agent": "Firefox/142.0"
    }
    
    data = {"entity_id": entity_id}

    try:
        requests.post(url, headers=headers, data=json.dumps(data), timeout=5)
        
    except Exception as e:
        print(f"Connection failed for {entity_id}: {e}")

    return None

if __name__ == "__main__":
    control_device("LivingRoom", "toggle")