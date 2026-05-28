#!/usr/bin/env python3
"""Create or update the Roadcall Fleet AI Dispatcher conversational flow + agent.

This is the SECOND vertical alongside Sandy (consumer roadside) and the Shop AI
Receptionist. It powers the per-tenant fleet roadside line a carrier publishes
to its drivers and dispatchers.

Routing on the backend: when an inbound Retell webhook arrives with
``agent_id == RETELL_FLEET_AGENT_ID``, ``retell_dispatch.create_service_request``
forks into ``_create_fleet_service_request`` which writes a
``RoadsideIncident`` for the carrier's organization instead of a consumer
public-job. No payment authorization step — fleets are billed on account.

Per-tenant context (company_name, organization_id, fleet phone, preferred
mechanic networks) is injected by the billing service at provisioning time via
``dynamic_variables``. Sentinel defaults live in this flow so first calls work
before any tenants exist.

Reads from env:
  RETELL_API_KEY                        (required)
  RETELL_BACKEND_WEBHOOK_TOKEN          (required; shared secret for tool auth)
  RETELL_BACKEND_URL or APP_BASE_URL    (required; public HTTPS, not localhost)
  RETELL_FLEET_AGENT_ID                 (optional; PATCH-updates existing agent)
  RETELL_FLEET_CONVERSATION_FLOW_ID     (optional; PATCH-updates existing flow)
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

RETELL_KEY = os.environ["RETELL_API_KEY"]
WEBHOOK_TOKEN = os.environ.get("RETELL_BACKEND_WEBHOOK_TOKEN", "local-dev-retell-token")
EXISTING_AGENT_ID = os.environ.get("RETELL_FLEET_AGENT_ID", "").strip()
EXISTING_FLOW_ID = os.environ.get("RETELL_FLEET_CONVERSATION_FLOW_ID", "").strip()
BACKEND_URL = (
    os.environ.get("RETELL_BACKEND_URL")
    or os.environ.get("APP_BASE_URL", "http://localhost:8000")
).rstrip("/")
if "localhost" in BACKEND_URL or "127.0.0.1" in BACKEND_URL:
    print("⚠️  APP_BASE_URL is localhost — Retell requires a public HTTPS URL.")
    print("   Set RETELL_BACKEND_URL=https://your-prod-domain.com and re-run.")
    sys.exit(1)


def retell(method: str, path: str, body: dict | None = None) -> dict:
    url = f"https://api.retellai.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {RETELL_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} {path}: {e.read().decode()}")
        raise


# ── Conversation flow ────────────────────────────────────────────────────────
AUTH_HEADERS = {"Authorization": f"Bearer {WEBHOOK_TOKEN}"}

GLOBAL_PROMPT = "\n".join([
    "You are the Roadcall AI dispatcher for the {{company_name}} fleet roadside line.",
    "Callers are commercial drivers or fleet dispatchers reporting a breakdown on a tractor, trailer, straight truck, bus, or RV.",
    "Identify yourself as 'Roadcall Fleet Dispatch for {{company_name}}'. If {{company_name}} is empty or the literal string 'company_name', just say 'Roadcall Fleet Dispatch'.",
    "HARD RULE — ONE QUESTION AT A TIME. Drivers are stressed and roadside. Short, calm sentences. No interrogations.",
    "ABSOLUTE FIRST PRIORITY — DRIVER SAFETY. Before anything else: 'First — are you and the truck off the roadway and in a safe spot?' If they say no or describe injury/fire/accident, IMMEDIATELY route to the emergency end node — tell them to hang up and call 911, and that the carrier dispatcher will be paged.",
    "MECHANICAL EXPERT MODE — sound like a dispatcher who understands diesel breakdowns. Capture unit number, tractor/trailer type, loaded or empty status, engine make if known, dash warning lights, active fault codes, and whether the unit can move. Ask only one targeted mechanical question per turn.",
    "When the driver gives the symptom, call intake_guide with caller_type=fleet. Use the returned questions and ticket_fields to capture a structured breakdown ticket for dispatch.",
    "For no-start: separate no-crank from crank-no-start, then ask about battery voltage or jump attempts, starter click, fuel level, recent filter work, and whether lights dim while cranking. For DPF/DEF/derate: ask about check-engine or stop-engine lights, DEF warnings, regen attempts, speed-limit derate, smoke, and whether it can limp safely.",
    "For air/brake issues: ask current PSI, whether air builds above 90 PSI, tractor vs trailer leak, spring brakes locked, and whether the unit is safe to move. For overheating/oil pressure: ask gauge behavior, coolant leak or steam, fan operation, oil pressure warning, and whether the engine has been shut down. For tires/trailers/reefers: ask tire position and size if visible, brake lockup, air line/electrical issue, reefer fuel, box temperature, and alarm code.",
    "Classify the next operational state as safe_to_drive, can_limp_to_shop, mobile_repair, tow_required, or out_of_service, but do not give repair instructions beyond basic safety guidance.",
    "Once safety is confirmed, capture in this order, one turn each: driver_name, truck_type, trailer_type if applicable, problem_type, a short problem_description, and any fault_codes the driver can read off the dash.",
    "CALL PHONE RULE: Use caller_phone from the Retell call metadata as callback_number whenever it is available. If caller_phone is missing and the backend cannot find the map-shared location, ask once: 'What phone number did you enter when you shared your location?' Then pass that number silently to create_dispatch_session and match_mechanic. The website code flow works without SMS.",
    "Then say 'I'm pulling up help now' and call create_dispatch_session early so a secure location link can be sent.",
    "Call create_service_request as soon as you have driver_safe + driver_name + problem_type + problem_description. The backend will recognize this as a fleet call (no payment authorization is required for fleet customers — they are billed on account).",
    "For location, call create_dispatch_session first and use any shared GPS the backend already attached from caller_phone. If no shared GPS is attached, tell the driver: 'Please open roadcall.ai/go in your browser and enter code [public_code], then tap Share My Location. Stay on the line with me.' Do not say you will text a link and do not call request_location for normal location capture.",
    "While waiting for the driver to share location, poll get_dispatch_session_status every 8–10 seconds. Speak ONLY the verified say field and best_match fields the tool returns. Never invent a mechanic name, ETA, or price.",
    "Once a mechanic is matched and confirmed, summarize: mechanic name, ETA, what they'll bring. Tell the driver the carrier dispatcher will get the same update by text.",
    "If matching fails or no mechanic is available in range, say so honestly: 'I can't find a mechanic in your area right now — I'm escalating to the on-call dispatcher who'll call you back within 5 minutes.' Do not hang up until you've called save_call_summary.",
    "Always pass tenant_id={{tenant_id}} (the carrier's organization_id) to every tool call.",
    "Voice style: warm, calm, professional. Sound like a senior fleet dispatcher who's been doing this for twenty years. Half-second pause between sentences. Say 'open roadcall dot ai slash go' and read the code slowly.",
    f"Backend base URL: {BACKEND_URL}",
])

TOOLS = [
    {
        "type": "custom",
        "tool_id": "tool-fleet-create-dispatch-session",
        "name": "create_dispatch_session",
        "description": "Create or reuse the durable Roadcall dispatch session for this live Retell call. Call early once caller phone and basic incident details are known. The response returns dispatch_session_id, public_code, and a secure roadcall.ai/go?t= location_url.",
        "url": f"{BACKEND_URL}/api/dispatch/create-session",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Always 'retell'"},
                "retell_call_id": {"type": "string"},
                "caller_phone": {"type": "string", "description": "Driver phone from Retell call metadata"},
                "caller_name": {"type": "string"},
                "problem_description": {"type": "string"},
                "problem_type": {"type": "string"},
                "vehicle_type": {"type": "string"},
                "tenant_id": {"type": "string", "description": "Carrier organization_id from {{tenant_id}}"},
            },
            "required": ["source"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-fleet-dispatch-session-status",
        "name": "get_dispatch_session_status",
        "description": "Poll the durable dispatch session created by create_dispatch_session. Call every 8–10 seconds after issuing the secure roadcall.ai/go?t= link. Speak only the returned say field and verified best_match fields.",
        "url": f"{BACKEND_URL}/api/dispatch/session-status",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "dispatch_session_id": {"type": "string", "description": "dispatch_session_id returned by create_dispatch_session"},
            },
            "required": ["dispatch_session_id"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-fleet-create-sr",
        "name": "create_service_request",
        "description": "Create the backend fleet RoadsideIncident. Call once driver_safe + driver_name + problem_type + problem_description are known. The backend recognizes the Fleet agent_id and forks into the fleet path — no payment auth required.",
        "url": f"{BACKEND_URL}/api/calls/create-service-request",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "retell_call_id":      {"type": "string", "description": "Retell call ID"},
                "agent_id":            {"type": "string", "description": "Always pass {{agent_id}} so the backend can route to the fleet path"},
                "direction":           {"type": "string", "description": "inbound or outbound"},
                "language":            {"type": "string", "description": "BCP-47 language code"},
                "driver_safe":         {"type": "boolean", "description": "Is the driver safe and off the roadway?"},
                "driver_name":         {"type": "string"},
                "callback_number":     {"type": "string", "description": "Driver's callback phone in E.164"},
                "company_name":        {"type": "string", "description": "Carrier / trucking company name. Use {{company_name}} from dynamic_variables when set."},
                "truck_type":          {"type": "string", "description": "tractor|box_truck|straight_truck|bus|rv|pickup_hotshot|other"},
                "trailer_type":        {"type": "string", "description": "dry_van|reefer|flatbed|step_deck|tanker|lowboy|container_chassis|none|other"},
                "loaded_status":       {"type": "string", "description": "loaded|empty|bobtail|unknown"},
                "problem_type":        {"type": "string", "description": "tire|coolant_leak|no_start|dead_battery|locked_brakes|air_leak|fuel_issue|reefer_issue|derate|overheating|regen_issue|electrical|accident_damage|other"},
                "problem_description": {"type": "string"},
                "fault_codes":         {"type": "array", "items": {"type": "string"}, "description": "Any fault/error codes the driver can read off the dash"},
                "caller_phone":        {"type": "string", "description": "Caller phone from Retell metadata if available"},
            },
            "required": ["retell_call_id", "driver_safe", "driver_name", "problem_type", "problem_description"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-fleet-request-loc",
        "name": "request_location",
        "description": "Legacy fallback only. Do not call for normal location capture. Prefer create_dispatch_session and tell the driver to open roadcall.ai/go with the returned public_code.",
        "url": f"{BACKEND_URL}/api/location/request",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "service_request_id": {"type": "string", "description": "service_request_id returned by create_service_request"},
                "callback_number":    {"type": "string", "description": "Driver phone for SMS"},
                "preferred_channel":  {"type": "string", "description": "Always 'sms'"},
                "sms_template_id":    {"type": "string", "description": "Always 'location_request'"},
                "manual_location_details": {
                    "type": "object",
                    "description": "Fallback when SMS fails — collect highway, mile marker, exit, city, state, nearest truck stop, direction of travel.",
                    "properties": {
                        "interstate_or_highway": {"type": "string"},
                        "mile_marker":           {"type": "string"},
                        "nearest_exit":          {"type": "string"},
                        "city":                  {"type": "string"},
                        "state":                 {"type": "string"},
                        "truck_stop":            {"type": "string"},
                        "landmark":              {"type": "string"},
                        "direction_of_travel":   {"type": "string"},
                    },
                },
            },
            "required": ["service_request_id"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-fleet-match-mechanic",
        "name": "match_mechanic",
        "description": "Fallback explicit mechanic search if get_dispatch_session_status hasn't returned a match within ~60 seconds. Pass city, state, problem_type and vehicle_type. Speak only fields the tool returns.",
        "url": f"{BACKEND_URL}/api/roadside/match-mechanic",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "message":      {"type": "string", "description": "Latest driver message or concise summary"},
                "city":         {"type": "string"},
                "state":        {"type": "string"},
                "problem_type": {"type": "string"},
                "vehicle_type": {"type": "string"},
                "tenant_id":    {"type": "string"},
            },
            "required": ["problem_type"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-fleet-intake-guide",
        "name": "intake_guide",
        "description": "Return symptom-specific dispatcher questions, structured ticket fields, and emergency flags. Call after the driver describes the breakdown symptom.",
        "url": f"{BACKEND_URL}/api/shop-ai/intake-guide",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "complaint": {"type": "string"},
                "vehicle_type": {"type": "string"},
                "caller_type": {"type": "string", "enum": ["shop", "fleet"], "description": "Always fleet"},
            },
            "required": ["tenant_id", "complaint"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-fleet-save-summary",
        "name": "save_call_summary",
        "description": "Persist a one-paragraph summary of the call just before ending. Call exactly once at the end whether the dispatch succeeded, escalated, or was declined.",
        "url": f"{BACKEND_URL}/api/shop-ai/save-call-summary",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id":      {"type": "string"},
                "retell_call_id": {"type": "string"},
                "caller_phone":   {"type": "string"},
                "summary":        {"type": "string"},
                "intent":         {"type": "string", "description": "Always 'fleet_roadside'"},
                "urgency":        {"type": "string", "description": "low|normal|high|emergency"},
                "problem_type":   {"type": "string"},
                "vehicle_type":   {"type": "string"},
                "key_points":     {"type": "array", "items": {"type": "string"}},
                "vehicle_intake": {
                    "type": "object",
                    "properties": {
                        "unit_number": {"type": "string"},
                        "year": {"type": "string"},
                        "make": {"type": "string"},
                        "model": {"type": "string"},
                        "mileage": {"type": "string"},
                        "vin": {"type": "string"},
                        "truck_type": {"type": "string"},
                        "trailer_type": {"type": "string"},
                        "loaded_status": {"type": "string"},
                        "engine_make": {"type": "string"},
                        "fault_codes": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "triage": {
                    "type": "object",
                    "properties": {
                        "symptom_category": {"type": "string"},
                        "classification": {"type": "string", "description": "safe_to_drive|can_limp_to_shop|mobile_repair|tow_required|out_of_service"},
                        "safe_to_drive": {"type": "boolean"},
                        "emergency_flags": {"type": "array", "items": {"type": "string"}},
                        "handoff_required": {"type": "boolean"},
                        "handoff_reason": {"type": "string"},
                    },
                },
                "post_call_automation": {
                    "type": "object",
                    "properties": {
                        "notify_fleet_manager": {"type": "boolean"},
                        "notify_owner": {"type": "boolean"},
                        "handoff_summary_sent": {"type": "boolean"},
                    },
                },
                "handoff_requested": {"type": "boolean"},
                "handoff_reason":   {"type": "string"},
                "transcript":     {"type": "string"},
            },
            "required": ["tenant_id", "retell_call_id", "summary"],
        },
    },
]

NODES = [
    {
        "id": "start-greeting",
        "type": "conversation",
        "display_position": {"x": 0, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": (
                "Greet calmly: 'Roadcall Fleet Dispatch for {{company_name}}. "
                "First — are you and the truck off the roadway and in a safe spot?' "
                "If {{company_name}} is empty or literal, drop that phrase and just say 'Roadcall Fleet Dispatch'."
            ),
        },
        "edges": [
            {
                "id": "edge-greet-to-emergency",
                "destination_node_id": "emergency-end",
                "transition_condition": {"type": "prompt", "prompt": "Driver reports they are NOT safe, are in traffic, are injured, or describes fire / crash / smoke."},
            },
            {
                "id": "edge-greet-to-collect",
                "destination_node_id": "collect-driver",
                "transition_condition": {"type": "prompt", "prompt": "Driver confirms they are safe and off the roadway."},
            },
        ],
    },
    {
        "id": "collect-driver",
        "type": "conversation",
        "display_position": {"x": 350, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": (
                "One question at a time: 'Got it — glad you're safe. Who am I speaking with?' "
                "Capture driver_name. Do not ask for a callback number for location."
            ),
        },
        "edges": [
            {
                "id": "edge-driver-to-vehicle",
                "destination_node_id": "collect-vehicle",
                "transition_condition": {"type": "prompt", "prompt": "Have driver_name."},
            }
        ],
    },
    {
        "id": "collect-vehicle",
        "type": "conversation",
        "display_position": {"x": 700, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": (
                "Ask: 'What are you driving — tractor, straight truck, box truck, bus, or RV?' "
                "Then: 'And the trailer — dry van, reefer, flatbed, tanker, or no trailer?' "
                "Capture truck_type, trailer_type, loaded_status if mentioned."
            ),
        },
        "edges": [
            {
                "id": "edge-vehicle-to-problem",
                "destination_node_id": "collect-problem",
                "transition_condition": {"type": "prompt", "prompt": "Have truck_type and trailer_type (or 'none')."},
            }
        ],
    },
    {
        "id": "collect-problem",
        "type": "conversation",
        "display_position": {"x": 1050, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": (
                "Ask: 'What's going on with the truck?' Capture a short problem_description. "
                "Then ask once: 'Any fault codes or warning lights on the dash you can read off to me?' Capture fault_codes as a list. "
                "Classify problem_type as one of: tire|coolant_leak|no_start|dead_battery|locked_brakes|air_leak|fuel_issue|reefer_issue|derate|overheating|regen_issue|electrical|accident_damage|other."
            ),
        },
        "edges": [
            {
                "id": "edge-problem-to-session",
                "destination_node_id": "create-session",
                "transition_condition": {"type": "prompt", "prompt": "Have problem_type and problem_description."},
            }
        ],
    },
    {
        "id": "create-session",
        "type": "conversation",
        "display_position": {"x": 1400, "y": 0},
        "name": "Create dispatch session",
        "instruction": {
            "type": "prompt",
            "text": (
                "Say briefly: 'Hang tight — pulling up help for you now.' Then invoke create_dispatch_session with "
                "source='retell', retell_call_id, caller_phone, caller_name=driver_name, problem_type, problem_description, "
                "vehicle_type=truck_type, and tenant_id={{tenant_id}}. Remember the returned dispatch_session_id and location_url."
            ),
        },
        "edges": [
            {
                "id": "edge-session-to-sr",
                "destination_node_id": "create-sr",
                "transition_condition": {"type": "prompt", "prompt": "create_dispatch_session returned a dispatch_session_id."},
            }
        ],
    },
    {
        "id": "create-sr",
        "type": "conversation",
        "display_position": {"x": 1750, "y": 0},
        "name": "Create service request",
        "instruction": {
            "type": "prompt",
            "text": (
                "Invoke create_service_request with retell_call_id, agent_id={{agent_id}}, driver_safe=true, driver_name, "
                "callback_number if call metadata has one, company_name={{company_name}}, truck_type, trailer_type, loaded_status, problem_type, "
                "problem_description, fault_codes, and caller_phone. Remember the returned service_request_id."
            ),
        },
        "edges": [
            {
                "id": "edge-sr-to-loc",
                "destination_node_id": "request-location",
                "transition_condition": {"type": "prompt", "prompt": "create_service_request returned a service_request_id."},
            }
        ],
    },
    {
        "id": "request-location",
        "type": "conversation",
        "display_position": {"x": 2100, "y": 0},
        "name": "Request location",
        "instruction": {
            "type": "prompt",
            "text": (
                "Do not call request_location for normal location capture. Use the dispatch_session_id and public_code returned by create_dispatch_session. "
                "Tell the driver: 'Please open roadcall.ai/go in your browser and enter code [public_code], then tap Share My Location. Stay on the line with me.' "
                "If the driver cannot use the website, collect manual location details: highway, mile marker, exit, nearest truck stop, city, state, and direction of travel."
            ),
        },
        "edges": [
            {
                "id": "edge-loc-to-poll",
                "destination_node_id": "poll-status",
                "transition_condition": {"type": "prompt", "prompt": "Location code was spoken or manual location collected."},
            }
        ],
    },
    {
        "id": "poll-status",
        "type": "conversation",
        "display_position": {"x": 2450, "y": 0},
        "name": "Poll dispatch status",
        "instruction": {
            "type": "prompt",
            "text": (
                "Make light conversation with the driver ('Where are you headed today?', 'What kind of freight are you running?'). "
                "Every 8–10 seconds invoke get_dispatch_session_status with the dispatch_session_id. "
                "Speak ONLY the returned 'say' field verbatim. When best_match is populated and confirmed, move to confirm-dispatch. "
                "If after several polls there's still no match, invoke match_mechanic once as a fallback with the city/state from the location response, "
                "then route to escalate-no-match."
            ),
        },
        "edges": [
            {
                "id": "edge-poll-to-confirm",
                "destination_node_id": "confirm-dispatch",
                "transition_condition": {"type": "prompt", "prompt": "A mechanic best_match has been confirmed with name and ETA."},
            },
            {
                "id": "edge-poll-to-escalate",
                "destination_node_id": "escalate-no-match",
                "transition_condition": {"type": "prompt", "prompt": "No mechanic match available after multiple polls and match_mechanic fallback."},
            },
        ],
    },
    {
        "id": "confirm-dispatch",
        "type": "conversation",
        "display_position": {"x": 2800, "y": -150},
        "instruction": {
            "type": "prompt",
            "text": (
                "Recap to the driver: '{{mechanic_name}} from {{mechanic_company}} is on the way — ETA about {{eta_minutes}} minutes. "
                "They'll bring {{equipment}} for your {{problem_type}}.' (Use only the verified fields from the last tool response — never invent.) "
                "Then: 'Your dispatcher at {{company_name}} is getting the same update by text. Anything else before I let you go?'"
            ),
        },
        "edges": [
            {
                "id": "edge-confirm-to-summary",
                "destination_node_id": "save-summary",
                "transition_condition": {"type": "prompt", "prompt": "Driver confirms they have what they need."},
            }
        ],
    },
    {
        "id": "escalate-no-match",
        "type": "conversation",
        "display_position": {"x": 2800, "y": 150},
        "instruction": {
            "type": "prompt",
            "text": (
                "Tell the driver honestly: 'I can't find a mechanic in your area right now — I'm escalating this to the on-call human dispatcher "
                "and they'll call you back within 5 minutes. Stay where you are and stay safe.' Do not pretend a match exists."
            ),
        },
        "edges": [
            {
                "id": "edge-escalate-to-summary",
                "destination_node_id": "save-summary",
                "transition_condition": {"type": "prompt", "prompt": "Driver acknowledges the escalation."},
            }
        ],
    },
    {
        "id": "save-summary",
        "type": "conversation",
        "display_position": {"x": 3150, "y": 0},
        "name": "Save summary",
        "instruction": {
            "type": "prompt",
            "text": (
                "Invoke save_call_summary with tenant_id={{tenant_id}}, retell_call_id, caller_phone=callback_number, "
                "a one-paragraph summary covering driver, vehicle, problem, location, mechanic match (or escalation), "
                "intent='fleet_roadside', and inferred urgency."
            ),
        },
        "edges": [
            {
                "id": "edge-summary-to-end",
                "destination_node_id": "end-call",
                "transition_condition": {"type": "prompt", "prompt": "Summary saved."},
            }
        ],
    },
    {
        "id": "end-call",
        "type": "end",
        "display_position": {"x": 3500, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": "Say: 'You're all set — Roadcall's got you. Drive safe out there.' Then end the call.",
        },
        "edges": [],
    },
    {
        "id": "emergency-end",
        "type": "end",
        "display_position": {"x": 350, "y": -300},
        "instruction": {
            "type": "prompt",
            "text": (
                "Say firmly and calmly: 'If anyone is hurt or in danger, hang up and call 911 right now. "
                "I'm paging your carrier dispatcher at {{company_name}} immediately. Once you're safe, call back and we'll get a mechanic moving.' "
                "Then end the call."
            ),
        },
        "edges": [],
    },
]

FLOW = {
    "start_speaker": "agent",
    "model_choice": {"type": "cascading", "model": "gpt-4.1"},
    "model_temperature": 0,
    "tool_call_strict_mode": True,
    "global_prompt": GLOBAL_PROMPT,
    "tools": TOOLS,
    "nodes": NODES,
    "start_node_id": "start-greeting",
}

# ── Create or update flow ────────────────────────────────────────────────────
if EXISTING_FLOW_ID:
    print(f"Updating existing Fleet Dispatcher flow: {EXISTING_FLOW_ID}")
    flow_resp = retell("PATCH", f"/update-conversation-flow/{EXISTING_FLOW_ID}", FLOW)
    flow_id = flow_resp.get("conversation_flow_id", EXISTING_FLOW_ID)
    print(f"✅ Flow updated: {flow_id}")
else:
    print("Creating Fleet Dispatcher conversational flow...")
    flow_resp = retell("POST", "/create-conversation-flow", FLOW)
    flow_id = flow_resp["conversation_flow_id"]
    print(f"✅ Flow created: {flow_id}")

# ── Create or update agent ──────────────────────────────────────────────────
agent_body = {
    "agent_name": "Fleet AI Dispatcher — Roadcall",
    "response_engine": {"type": "conversation-flow", "conversation_flow_id": flow_id},
    "voice_id": "retell-Cimo",
    "language": "en-US",
    "interruption_sensitivity": 0.55,
    "responsiveness": 0.8,
    "voice_speed": 0.95,
    "voice_temperature": 0.7,
    "enable_backchannel": True,
    "backchannel_frequency": 0.45,
    "backchannel_words": ["okay", "got it", "mm-hmm", "copy that", "understood"],
    "max_call_duration_ms": 2700000,  # 45 min — fleet calls can run long while polling
    "end_call_after_silence_ms": 90000,
    "boosted_keywords": [
        "tractor", "trailer", "reefer", "dry van", "flatbed", "tanker", "lowboy",
        "DEF", "derate", "regen", "fault code", "check engine", "air leak",
        "coolant", "tire", "blowout", "drive tire", "steer tire", "trailer tire",
        "no start", "dead battery", "alternator", "starter", "fuel filter",
        "DOT", "ELD", "mile marker", "interstate", "truck stop",
        "dispatcher", "carrier", "owner operator", "fleet",
    ],
    "normalize_for_speech": True,
}

if EXISTING_AGENT_ID:
    print(f"\nUpdating existing Fleet Dispatcher agent: {EXISTING_AGENT_ID}")
    agent_resp = retell("PATCH", f"/update-agent/{EXISTING_AGENT_ID}", agent_body)
    agent_id = agent_resp.get("agent_id", EXISTING_AGENT_ID)
    print(f"✅ Agent updated: {agent_id}")
else:
    print("\nCreating Fleet Dispatcher agent...")
    agent_resp = retell("POST", "/create-agent", agent_body)
    agent_id = agent_resp["agent_id"]
    print(f"✅ Agent created: {agent_id}")

print(f"\n{'='*60}")
print(f"  Fleet Conversation Flow ID : {flow_id}")
print(f"  Fleet Agent ID             : {agent_id}")
print(f"  Backend URL                : {BACKEND_URL}")
print(f"{'='*60}")
print("\nNext steps:")
print(f"  1. Set RETELL_FLEET_AGENT_ID={agent_id} in DO env (and locally in .env)")
print(f"  2. Set RETELL_FLEET_CONVERSATION_FLOW_ID={flow_id} in DO env")
print("  3. Per-carrier agents will be spawned by the billing service activate_ai flow")
print("     when a fleet customer onboards; this script provisions the master flow + reference agent.")
print("  4. Verify RETELL_BACKEND_WEBHOOK_TOKEN matches the backend env var.")
