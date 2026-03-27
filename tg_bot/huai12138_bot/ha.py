import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("HA_URL", "http://192.168.1.100:8123")
TOKEN = os.getenv("HA_TOKEN", "your_long_lived_token_here")

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
    url = f"{URL}/api/services/switch/{action}"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Firefox/142.0"
    }
    
    data = {"entity_id": entity_id}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        
        if response.status_code == 200:
            print(f"Successfully sent {action} command to {entity_id}")
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Connection failed for {entity_id}: {e}")

    return None

if __name__ == "__main__":
    control_device("LivingRoom", "turn_off")