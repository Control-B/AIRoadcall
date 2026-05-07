#!/usr/bin/env python3
"""Assign Telnyx number to messaging profile and send a test SMS."""
import httpx, sys

import os
API_KEY = os.environ.get("TELNYX_API_KEY", "")
FROM_NUMBER = "+17275584572"
TEST_TO = "+17272728156"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 1. Get messaging profile
r = httpx.get("https://api.telnyx.com/v2/messaging_profiles", headers=HEADERS)
profiles = r.json().get("data", [])
if not profiles:
    print("ERROR: No messaging profiles found. Create one in Telnyx dashboard.")
    sys.exit(1)
profile_id = profiles[0]["id"]
print(f"Messaging profile: {profile_id} ({profiles[0].get('name')})")

# 2. Assign number to profile
r = httpx.patch(
    f"https://api.telnyx.com/v2/phone_numbers/%2B17275584572",
    headers=HEADERS,
    json={"messaging_profile_id": profile_id},
)
assigned = r.json().get("data", {}).get("messaging_profile_id")
print(f"Number assigned to profile: {assigned}")

# 3. Send test SMS
r = httpx.post(
    "https://api.telnyx.com/v2/messages",
    headers=HEADERS,
    json={"from": FROM_NUMBER, "to": TEST_TO, "text": "Roadcall test — SMS is live! 🚗🔧"},
)
data = r.json()
if "errors" in data:
    print(f"SMS ERROR: {data['errors']}")
else:
    print(f"SMS sent! id={data.get('data',{}).get('id')}, status={data.get('data',{}).get('to',[{}])[0].get('status')}")
