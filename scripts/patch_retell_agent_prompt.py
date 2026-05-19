#!/usr/bin/env python3
"""Push the latest prompt AND webhook tool URLs to live Retell agents.

Usage (only RETELL_API_KEY is required — run anywhere):

    # Set your key, then run
    export RETELL_API_KEY=key_xxxxxxxx

    # Update all agents whose IDs are known (reads from env or hardcoded IDs)
    python3 scripts/patch_retell_agent_prompt.py

    # Update a specific agent by ID
    python3 scripts/patch_retell_agent_prompt.py agent_abc123

    # List all agents in your Retell account
    python3 scripts/patch_retell_agent_prompt.py --list

    # Dry-run: print what would be sent without calling the API
    python3 scripts/patch_retell_agent_prompt.py --dry-run

Optional env overrides (defaults shown in KNOWN_AGENTS below):
    RETELL_AGENT_ID, RETELL_FLEET_AGENT_ID, RETELL_SHOP_AGENT_ID,
    APP_BASE_URL  (default: https://airoadcall-i76ba.ondigitalocean.app)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ─── pull in the canonical prompt template from the app ───────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

try:
    from app.services.retell_provisioning_service import SERVICE_ADVISOR_PROMPT_TEMPLATE
except ImportError:
    print("ERROR: Could not import SERVICE_ADVISOR_PROMPT_TEMPLATE from app.")
    print("       Run from the repo root or activate the backend venv first.")
    sys.exit(1)

RETELL_BASE = "https://api.retellai.com/v2"

# ─── known agent IDs (can be overridden by env vars) ──────────────────────────
KNOWN_AGENTS: dict[str, dict] = {
    "roadside": {
        "env_var": "RETELL_AGENT_ID",
        "default_id": "agent_c55f3b83dd7614ba0be6bec7e4",
        "label": "Roadcall Roadside Dispatch",
        "tools": "roadside",
    },
    "fleet": {
        "env_var": "RETELL_FLEET_AGENT_ID",
        "default_id": "agent_de6a05ee2707364b82883974ad",
        "label": "Roadcall Fleet",
        "tools": "roadside",   # fleet uses same dispatch flow as roadside
    },
    "shop": {
        "env_var": "RETELL_SHOP_AGENT_ID",
        "default_id": "agent_9edfdf87e375eeffba42912a6f",
        "label": "Roadcall Shop / Mechanic",
        "tools": "shop",       # shop uses separate appointment/service flow
    },
}


def _base_url() -> str:
    return os.environ.get("APP_BASE_URL", "https://airoadcall-i76ba.ondigitalocean.app").rstrip("/")


def _roadside_tools() -> list[dict]:
    """Webhook tools for the roadside and fleet agents."""
    base = _base_url()
    return [
        {
            "type": "webhook",
            "name": "save_driver_info",
            "description": (
                "Call this at the start of every roadside call. "
                "Pass driver_name, vehicle_type, issue_type, situation_note. "
                "Returns a 4-digit location code for the agent to speak to the caller."
            ),
            "url": f"{base}/api/retell/save-driver-info",
            "method": "POST",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Setting up your location code now.",
        },
        {
            "type": "webhook",
            "name": "check_location",
            "description": (
                "Poll whether the caller has opened roadcall.ai/go and shared GPS. "
                "Pass location_code returned by save_driver_info. "
                "Call every 15 seconds until GPS is confirmed."
            ),
            "url": f"{base}/api/retell/check-location",
            "method": "POST",
            "speak_during_execution": False,
            "speak_after_execution": True,
            "execution_message_description": "Checking your location.",
        },
        {
            "type": "webhook",
            "name": "find_nearby_mechanics",
            "description": (
                "Search for available mechanics near the confirmed GPS location. "
                "Pass job_code, issue_type, vehicle_type. "
                "Call only after check_location confirms GPS received."
            ),
            "url": f"{base}/api/retell/find-mechanics",
            "method": "POST",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Searching for nearby mechanics.",
        },
    ]


def _shop_tools() -> list[dict]:
    """Webhook tools for the shop / mechanic receptionist agent."""
    base = _base_url()
    return [
        {
            "type": "webhook",
            "name": "create_service_request",
            "description": "Create a service request or appointment for a shop caller.",
            "url": f"{base}/api/calls/create-service-request",
            "method": "POST",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Creating your service request.",
        },
        {
            "type": "webhook",
            "name": "request_location",
            "description": "Send a location request link to the caller.",
            "url": f"{base}/api/location/request",
            "method": "POST",
            "speak_during_execution": False,
            "speak_after_execution": True,
            "execution_message_description": "Requesting your location.",
        },
        {
            "type": "webhook",
            "name": "location_status",
            "description": "Check whether the caller has shared their GPS location.",
            "url": f"{base}/api/location/status",
            "method": "POST",
            "speak_during_execution": False,
            "speak_after_execution": True,
            "execution_message_description": "Checking location status.",
        },
        {
            "type": "webhook",
            "name": "dispatch_status",
            "description": "Check the current dispatch status for a service request.",
            "url": f"{base}/api/dispatch/status",
            "method": "POST",
            "speak_during_execution": False,
            "speak_after_execution": True,
            "execution_message_description": "Checking dispatch status.",
        },
        {
            "type": "webhook",
            "name": "confirm_dispatch",
            "description": "Confirm a mechanic dispatch for the caller.",
            "url": f"{base}/api/dispatch/confirm",
            "method": "POST",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Confirming dispatch.",
        },
        {
            "type": "webhook",
            "name": "request_payment",
            "description": "Send a payment request to the caller.",
            "url": f"{base}/api/payment/request",
            "method": "POST",
            "speak_during_execution": True,
            "speak_after_execution": True,
            "execution_message_description": "Sending payment request.",
        },
        {
            "type": "webhook",
            "name": "warm_transfer",
            "description": "Transfer the call to a live dispatcher or mechanic.",
            "url": f"{base}/api/transfer/warm",
            "method": "POST",
            "speak_during_execution": True,
            "speak_after_execution": False,
            "execution_message_description": "Connecting you now.",
        },
    ]


def _api_key() -> str:
    key = os.environ.get("RETELL_API_KEY", "").strip()
    if not key:
        print("ERROR: RETELL_API_KEY is not set.")
        print("       export RETELL_API_KEY=key_xxxxxxxx  then re-run.")
        sys.exit(1)
    return key


def _request(method: str, path: str, body: dict | None = None, dry_run: bool = False) -> dict:
    if dry_run:
        print(f"  [dry-run] {method} {RETELL_BASE}{path}")
        if body:
            preview = json.dumps(body, indent=2)[:600]
            print(f"  payload preview:\n{preview}")
        return {}
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
        print(f"  Retell API error {exc.code}: {detail}")
        sys.exit(1)


def list_agents() -> None:
    print("Fetching agents from Retell API...")
    agents = _request("GET", "/list-agents")
    if isinstance(agents, list):
        for a in agents:
            print(f"  {a.get('agent_id')}  name={a.get('agent_name', '(unnamed)')}")
    else:
        print(json.dumps(agents, indent=2))


def _build_prompt() -> str:
    return SERVICE_ADVISOR_PROMPT_TEMPLATE.format(
        shop_name="Roadcall",
        shop_address="Mobile roadside dispatch",
        hourly_rate="Contact dispatch",
        mobile_service_available=True,
        service_radius_miles=75,
        after_hours_mode="capture_and_escalate",
        dispatch_phone="contact dispatch",
        fleet_priority_accounts=[],
        supported_services=[
            "tire", "no_start", "air_leak", "dpf_derate",
            "electrical", "trailer_repair", "overheating", "towing", "pm_service",
        ],
        supported_engines=[],
    )


def patch_agent(agent_id: str, tools_type: str = "roadside", label: str = "", dry_run: bool = False) -> None:
    tools = _roadside_tools() if tools_type == "roadside" else _shop_tools()
    prompt = _build_prompt()
    display = label or agent_id
    print(f"\nPatching {display} ({agent_id}) ...")
    print(f"  prompt length: {len(prompt)} chars")
    print(f"  tools: {[t['name'] for t in tools]}")
    result = _request(
        "PATCH",
        f"/update-agent/{agent_id}",
        {"general_prompt": prompt, "general_tools": tools},
        dry_run=dry_run,
    )
    if not dry_run:
        print(f"  Done — agent_id={result.get('agent_id')}  name={result.get('agent_name', '?')}")


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    if "--list" in args:
        list_agents()
        return

    if dry_run:
        print("=== DRY RUN — no API calls will be made ===\n")

    if args:
        # Explicit agent IDs on command line — use roadside tools by default
        for agent_id in args:
            patch_agent(agent_id.strip(), tools_type="roadside", dry_run=dry_run)
        return

    # Default: patch all known agents
    patched = 0
    for role, cfg in KNOWN_AGENTS.items():
        agent_id = os.environ.get(cfg["env_var"], cfg["default_id"]).strip()
        if agent_id:
            patch_agent(agent_id, tools_type=cfg["tools"], label=cfg["label"], dry_run=dry_run)
            patched += 1

    if patched == 0:
        print("No agent IDs found. Check KNOWN_AGENTS in this script or pass an ID as argument.")
        sys.exit(1)

    if not dry_run:
        print(f"\nAll {patched} agents updated.")


if __name__ == "__main__":
    main()

