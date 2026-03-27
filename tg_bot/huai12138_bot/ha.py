import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# No default values to ensure it crashes early if env is missing
ha_url = os.getenv("HA_URL")
ha_token = os.getenv("HA_TOKEN")

if not ha_url or not ha_token:
    raise ValueError("Missing HA_URL or HA_TOKEN")

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

# Change to 'async def'
async def control_device(room_name, action="toggle"):
    entity_id = DEVICE_MAP.get(room_name.lower())
    if not entity_id:
        return False
        
    real_action = ACTION_MAP.get(action.lower(), "toggle")
    url = f"{ha_url}/api/services/switch/{real_action}"
    
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    
    data = {"entity_id": entity_id}

    try:
        # Use AsyncClient to prevent blocking
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, headers=headers, json=data, timeout=10.0)
            return response.status_code == 200
    except Exception as e:
        print(f"HA Sync Error: {e}")
        return False