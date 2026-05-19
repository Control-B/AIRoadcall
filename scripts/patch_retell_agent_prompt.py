#!/usr/bin/env python3
"""Push the latest SERVICE_ADVISOR_PROMPT_TEMPLATE to one or more live Retell agents.

Usage (run on the server where env vars are set):

    # Update the default roadside agent (RETELL_AGENT_ID)
    python3 scripts/patch_retell_agent_prompt.py

    # Update a specific agent by ID
    python3 scripts/patch_retell_agent_prompt.py agent_abc123

    # List all agents so you can find IDs
    python3 scripts/patch_retell_agent_prompt.py --list

Reads: RETELL_API_KEY, RETELL_AGENT_ID, RETELL_FLEET_AGENT_ID, RETELL_SHOP_AGENT_ID
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ─── pull in the canonical template from the app ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

try:
    from app.services.retell_provisioning_service import SERVICE_ADVISOR_PROMPT_TEMPLATE
except ImportError:
    print("ERROR: Could not import SERVICE_ADVISOR_PROMPT_TEMPLATE from app.")
    print("       Run this script from the repo root or with the backend venv active.")
    sys.exit(1)

RETELL_BASE = "https://api.retellai.com/v2"


def _api_key() -> str:
    key = os.environ.get("RETELL_API_KEY", "").strip()
    if not key:
        print("ERROR: RETELL_API_KEY environment variable is not set.")
        sys.exit(1)
    return key


def _request(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{RETELL_BASE}{path}",
        data=data,
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:600]
        print(f"Retell API error {exc.code}: {detail}")
        sys.exit(1)


def list_agents() -> None:
    agents = _request("GET", "/list-agents")
    if isinstance(agents, list):
        for a in agents:
            print(f"  {a.get('agent_id')}  name={a.get('agent_name', '(unnamed)')}")
    else:
        print(json.dumps(agents, indent=2))


def patch_agent(agent_id: str) -> None:
    # Build a generic prompt for patching (uses placeholder shop info).
    # Roadcall's platform replaces these at call-start via dynamic variables.
    prompt = SERVICE_ADVISOR_PROMPT_TEMPLATE.format(
        shop_name="Roadcall",
        shop_address="Mobile roadside dispatch",
        hourly_rate="Contact dispatch",
        mobile_service_available=True,
        service_radius_miles=75,
        after_hours_mode="capture_and_escalate",
        dispatch_phone="contact dispatch",
        fleet_priority_accounts=[],
        supported_services=["tire", "no_start", "air_leak", "dpf_derate",
                             "electrical", "trailer_repair", "overheating",
                             "towing", "pm_service"],
        supported_engines=[],
    )

    print(f"\nPatching agent {agent_id} ...")
    result = _request("PATCH", f"/update-agent/{agent_id}", {"general_prompt": prompt})
    print(f"Done — agent_id={result.get('agent_id')}  name={result.get('agent_name', '?')}")


def main() -> None:
    args = sys.argv[1:]

    if "--list" in args:
        print("Listing all Retell agents:")
        list_agents()
        return

    if args:
        # Explicit agent IDs passed on command line
        for agent_id in args:
            patch_agent(agent_id.strip())
        return

    # Default: patch every configured agent ID from env
    candidates = {
        "RETELL_AGENT_ID": os.environ.get("RETELL_AGENT_ID", "").strip(),
        "RETELL_FLEET_AGENT_ID": os.environ.get("RETELL_FLEET_AGENT_ID", "").strip(),
        "RETELL_SHOP_AGENT_ID": os.environ.get("RETELL_SHOP_AGENT_ID", "").strip(),
    }
    patched = 0
    for env_name, agent_id in candidates.items():
        if agent_id:
            print(f"\nUsing {env_name}={agent_id}")
            patch_agent(agent_id)
            patched += 1

    if patched == 0:
        print("No agent IDs found in environment. Set RETELL_AGENT_ID or pass one as argument.")
        print("Run with --list to see all agents in your Retell account.")
        sys.exit(1)


if __name__ == "__main__":
    main()
