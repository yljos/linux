import httpx
import os
import asyncio  # Required for running async code in __main__
# from dotenv import load_dotenv

# load_dotenv()

# # No default values to ensure it crashes early if env is missing
# ha_url = os.getenv("HA_URL")
# ha_token = os.getenv("HA_TOKEN")

# if not ha_url or not ha_token:
#     raise ValueError("Missing HA_URL or HA_TOKEN")

DEVICE_MAP = {
    "livingroom": "switch.zimi_cn_1057102723_dhkg01_on_p_2_1",
    "bedroom": "switch.zimi_cn_1021887790_dhkg01_on_p_2_1",
    "kitchen": "switch.zimi_cn_1054932941_dhkg01_on_p_2_1",
}

ACTION_MAP = {"on": "turn_on", "off": "turn_off", "toggle": "toggle"}

async def control_device(room_name, action="toggle"):
    """
    Control HA switches asynchronously using httpx.
    Returns True if status_code is 200, otherwise False.
    """
    entity_id = DEVICE_MAP.get(room_name.lower())
    if not entity_id:
        print(f"Error: Room '{room_name}' not found in DEVICE_MAP")
        return False

    real_action = ACTION_MAP.get(action.lower(), "toggle")
    url = f"{ha_url}/api/services/switch/{real_action}"

    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
        "User-Agent": "Firefox/142.0",
    }

    data = {"entity_id": entity_id}

    try:
        # Use AsyncClient to prevent blocking the bot's event loop
        async with httpx.AsyncClient(verify=True) as client:
            response = await client.post(url, headers=headers, json=data, timeout=10.0)
            if response.status_code == 200:
                print(f"Success: {room_name} -> {real_action}")
                return True
            else:
                print(f"HA API Error: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        print(f"Connection Error: {e}")
        return False

if __name__ == "__main__":
    # Correct way to run an async function from a synchronous script
    print("--- Starting HA Test ---")
    result = asyncio.run(control_device("livingroom", "toggle"))
    print(f"Test Result: {result}")