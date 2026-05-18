#!/usr/bin/env python3
"""Update DigitalOcean app env vars and re-deploy."""
import json, subprocess, sys

APP_ID = "8b291421-e807-4ad6-b00d-3217ebd3ee8e"

UPDATES = {
    "RETELL_BACKEND_WEBHOOK_TOKEN": "pFskGKL-SZpTkDBuswNLDtJlpMCgva5vXg2gnloFRhw",
    "APP_BASE_URL": "https://airoadcall-i76ba.ondigitalocean.app",
    "RETELL_AGENT_ID": "agent_c55f3b83dd7614ba0be6bec7e4",
    "RETELL_CONVERSATION_FLOW_ID": "conversation_flow_9830b2d0fa37",
    "RETELL_SHOP_AGENT_ID": "agent_9edfdf87e375eeffba42912a6f",
    "RETELL_SHOP_CONVERSATION_FLOW_ID": "conversation_flow_6765418d421c",
    "RETELL_FLEET_AGENT_ID": "agent_de6a05ee2707364b82883974ad",
    "RETELL_FLEET_CONVERSATION_FLOW_ID": "conversation_flow_9c91cb43d4d9",
}

# Fetch current spec
result = subprocess.run(
    ["doctl", "apps", "get", APP_ID, "--output", "json"],
    capture_output=True, text=True
)
if result.returncode != 0:
    print("Error fetching app:", result.stderr)
    sys.exit(1)

d = json.loads(result.stdout)
# doctl returns a list when using --output json
app = d[0] if isinstance(d, list) else d["app"]
spec = app["spec"]

changed = []
for svc in spec.get("services", []) + spec.get("workers", []) + spec.get("jobs", []):
    envs = svc.get("envs", [])
    existing_keys = {e["key"] for e in envs}
    for key, val in UPDATES.items():
        found = False
        for env in envs:
            if env["key"] == key:
                env["value"] = val
                if key == "RETELL_BACKEND_WEBHOOK_TOKEN":
                    env["type"] = "SECRET"
                changed.append(f"  updated {key} in {svc['name']}")
                found = True
                break
        if not found:
            new_env = {"key": key, "value": val}
            if key == "RETELL_BACKEND_WEBHOOK_TOKEN":
                new_env["type"] = "SECRET"
            envs.append(new_env)
            changed.append(f"  added {key} to {svc['name']}")
    svc["envs"] = envs

if not changed:
    print("No services/workers found with envs — check app structure")
    for k in spec:
        print(" ", k, type(spec[k]))
    sys.exit(1)

print("Changes:")
for c in changed:
    print(c)

spec_path = "/tmp/do_spec_updated.json"
json.dump(spec, open(spec_path, "w"), indent=2)
print(f"\nSpec written to {spec_path}")

result = subprocess.run(
    ["doctl", "apps", "update", APP_ID, "--spec", spec_path],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("✅ DO app updated — deploy triggered")
    print(result.stdout[:300])
else:
    print("❌ Error:", result.stderr[:500])
    sys.exit(1)
