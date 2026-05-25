#!/usr/bin/env python3
"""
Create the Roadcall.ai Sandy conversational flow agent in Retell.
Reads RETELL_API_KEY and RETELL_BACKEND_WEBHOOK_TOKEN from .env.
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

RETELL_KEY    = os.environ["RETELL_API_KEY"]
WEBHOOK_TOKEN = os.environ.get("RETELL_BACKEND_WEBHOOK_TOKEN", "local-dev-retell-token")
EXISTING_AGENT_ID = os.environ.get("RETELL_AGENT_ID", "").strip()
EXISTING_FLOW_ID = os.environ.get("RETELL_CONVERSATION_FLOW_ID", "").strip()
EXPORT_JSON_PATH = os.environ.get("RETELL_EXPORT_JSON", "").strip()
# RETELL_BACKEND_URL overrides everything (must be public HTTPS for Retell)
BACKEND_URL   = (
    os.environ.get("RETELL_BACKEND_URL")
    or os.environ.get("APP_BASE_URL", "http://localhost:8000")
).rstrip("/")
# Retell rejects localhost URLs; require a real URL
if "localhost" in BACKEND_URL or "127.0.0.1" in BACKEND_URL:
    print("⚠️  APP_BASE_URL is localhost — Retell requires a public HTTPS URL.")
    print("   Set RETELL_BACKEND_URL=https://your-prod-domain.com and re-run.")
    sys.exit(1)
if not EXPORT_JSON_PATH:
    if not os.environ.get("RETELL_BACKEND_WEBHOOK_TOKEN", "").strip():
        print("⚠️  RETELL_BACKEND_WEBHOOK_TOKEN is not set — refusing to publish Retell tools with the local-dev token.")
        print("   Run from the DigitalOcean app environment or export the production webhook token first.")
        sys.exit(1)
    if not EXISTING_AGENT_ID:
        print("⚠️  RETELL_AGENT_ID is not set — refusing to create a new unconnected Sandy agent.")
        print("   Set RETELL_AGENT_ID to the live Sandy agent connected to the phone number, then re-run.")
        sys.exit(1)

def retell(method: str, path: str, body: dict | None = None) -> dict:
    url = f"https://api.retellai.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method.upper(),
        headers={
            "Authorization": f"Bearer {RETELL_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print(f"HTTP {e.code} {path}: {msg}")
        raise

# ── Conversation flow definition ──────────────────────────
FLOW = {
    "start_speaker": "agent",
    "model_choice": {
        "type": "cascading",
        "model": "gpt-4.1"
    },
    "model_temperature": 0,
    "tool_call_strict_mode": True,

    "global_prompt": "\n".join([
        "You are Roadcall’s AI roadside dispatcher.",
        "Your primary job is: greet, get the caller's name, ask what they need help with, use the caller's pre-shared GPS from the Roadcall map phone button when available, then search the private mechanic directory with verified caller facts.",
        "Roadcall has a private mechanic directory available through the match_mechanic function. Never claim exact directory counts or coverage unless the tool response says so.",
        "HARD RULE — MINIMUM QUESTIONS: Ask ONLY four things before the first search. (1) Name. (2) What they need help with / problem. (3) City and state if missing. (4) Vehicle type if missing. Do not ask about road, highway, exit, landmark, mile marker, GPS, cross street, company, callback, email, payment, insurance, license plate, or address before the mechanic search.",
        "CALL FACTS LEDGER: Silently maintain caller_name, problem_type, problem_description, vehicle_type, city, state, dispatch_session_id, caller_gps_available, and selected_mechanic. Once the caller says a fact or a tool returns it, treat it as locked for the rest of the call. Never ask for a locked fact again.",
        "BEFORE EVERY QUESTION: Check the ledger and transcript. If the answer appears anywhere earlier in the call, update the ledger and move forward instead of asking. If you need to verify a possibly misheard fact, confirm it briefly: 'I have [fact] - is that right?' Do not use the original open-ended question again.",
        "Normalize common answers without asking again: flat, blowout, spare, tire off rim, and low air mean problem_type=tire; won't start, dead battery, no crank, and crank no start mean problem_type=no_start or battery as stated; semi, tractor, eighteen-wheeler, rig, box truck, pickup, car, trailer, RV, and fleet vehicle are valid vehicle_type answers.",
        "LOCATION RULE: The caller's phone number and GPS are captured before the call when the driver taps the green phone button on the Roadcall map. Never direct the caller to a website, browser page, link, text message, code, or alternate location-sharing flow.",
        "Immediately after the caller gives their name, call create_dispatch_session with caller_phone from Retell metadata and caller_name. Then call get_dispatch_session_status before asking what is wrong. If location_captured is true, verbally confirm the returned address/city in one sentence: 'I see your shared location near [address/city]. Is that correct?' Only after confirmation, ask what problem they are having.",
        "If location_captured is true, use that backend GPS for matching. Only use a caller-stated city instead when the caller explicitly says to search that city instead of their shared GPS.",
        "'Mechanic in Lakeland' means search Lakeland — do not ask which part of Lakeland before the first search. The tool can return nearby options automatically.",
        "At the start of the call only, say exactly: 'Thanks for calling Roadcall. This is Sandy. Who am I speaking with?' Then allow the caller to answer. Next ask exactly: 'What can I help you with today?' Never repeat the welcome after the caller answers.",
        "If city is missing: 'What city and state are you in?' If state is missing: 'What state is that in?' If problem is missing: 'What problem are you having — tire, engine, battery, fuel, towing, or something else?' If vehicle type is missing: 'What type of vehicle is it — car, pickup, box truck, semi, trailer, RV, or fleet vehicle?' Ask only ONE of these per turn, and only if truly missing.",
        "MECHANICAL EXPERT MODE: once the basic city/state/problem/vehicle search facts are captured, ask at most one targeted follow-up if it changes dispatch choice. For no-start, distinguish no-crank from crank-no-start. For diesel derate or DPF/DEF, ask about warning lights, regen attempts, DEF warnings, and whether the vehicle can limp safely. For air/brake issues, ask current PSI, air leak source, and brake lockup. For overheating or oil pressure, ask if the engine is shut down and whether there is coolant, steam, or an oil pressure warning. For tire/trailer/reefer issues, ask position, tire size if visible, brake/electrical/air issue, reefer temperature, fuel, and alarm code.",
        "Use mechanical details to classify safe_to_drive, can_limp_to_shop, mobile_repair, tow_required, or out_of_service. Never give step-by-step repair advice; focus on safe triage and matching the right mechanic.",
        "Never repeat a question the caller already answered. If you already heard 'Lakeland Florida' you have the city and state. If you already heard 'tire' you have the problem. If you already heard car, pickup, box truck, semi, trailer, RV, or fleet vehicle, you have the vehicle type. If a tool says needsMoreInfo for a fact already in the ledger, re-call the tool with the ledger value instead of asking the caller again.",
        "ABSOLUTE ANTI-HALLUCINATION RULE: You may ONLY speak a mechanic businessName, phone, address, or city that came verbatim from the latest match_mechanic tool response. Never invent or recall a mechanic from training data or memory. If match_mechanic has not been called yet in this call, you have no mechanic to offer.",
        "DURABLE SESSION RULE: As soon as caller_name is known, call create_dispatch_session with source='retell', retell_call_id when available, caller_phone when available, and caller_name. Do this before asking for the roadside issue so the backend can attach the map-shared GPS session. Later, call create_dispatch_session again with the same dispatch facts when problem_type or vehicle_type becomes known; the backend will reuse the same session.",
        "CALL METADATA RULE: Always pass caller_phone from Retell call metadata into create_dispatch_session. This is how the backend matches the map-shared GPS to the inbound call. Never ask the caller for their phone number.",
        "LOCATION FALLBACK RULE: Trust the backend tools for pre-shared GPS. If GPS is on file, continue to mechanic search. If no GPS is on file, ask verbally for highway or interstate, mile marker or nearest exit, city and state, and a nearby truck stop or landmark.",
        "SESSION STATUS POLLING: If you have dispatch_session_id, poll get_dispatch_session_status every 8 to 10 seconds. Speak only the returned say field and verified best_match fields.",
        "PACING: Speak like a calm human dispatcher, not a robot. When you read match_mechanic.message, honor the ellipses (\"...\") and periods as real pauses — take a half-second breath at each ellipsis and a full beat at each period. Do not run sentences together. Read each numbered option as its own sentence: \"Number one ... Truck Tire LLC ... \" pause ... \"Number two ... Big Guy Truck ... \" pause ... \"Number three ... Bobby's Truck Shop.\" Then ask the question. Never list more than three local options.",
        "When reading results, ALWAYS prefer to speak match_mechanic.message exactly as returned — it is already worded for voice and may include up to three local options and one major vendor when one is nearby. Never list more than three local options. After reading the message, ask one short next-step question. Do not read phone numbers unless the caller asks or picks one.",
        "The major vendor is provided in match_mechanic.majorVendor with brandName, interstate, and exitNumber. You may speak its brandName, interstate, exit, and city verbatim — but only if majorVendor is present in the latest tool response. Never invent a major vendor.",
        "If match_mechanic returns zero matches AND no majorVendor, do NOT name any business — go to manual dispatch.",
        "Never claim a mechanic is dispatched, confirmed, nearby, or en route unless backend dispatch status explicitly says so.",
        "If the driver mentions injury, fire, or danger, tell them to call 911 immediately.",
        "Never describe APIs, webhooks, tokens, or database internals to the caller.",
        f"Backend base URL: {BACKEND_URL}",
    ]),

    "tools": [
        {
            "type": "custom",
            "tool_id": "tool-roadcall-create-dispatch-session",
            "name": "create_dispatch_session",
            "description": "Create or reuse the durable Roadcall dispatch session for this live Retell call. Call this immediately after caller_name is known, before asking the issue. Always pass caller_phone from Retell call metadata so the backend can attach GPS already shared from the Roadcall map phone button. Use dispatch_session_id for backend polling. Do not speak any returned location code, URL, or link to the caller.",
            "url": f"{BACKEND_URL}/api/dispatch/create-session",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Always 'retell'"},
                    "retell_call_id": {"type": "string", "description": "Retell call ID when available"},
                    "twilio_call_sid": {"type": "string", "description": "Twilio CallSid when available"},
                    "caller_phone": {"type": "string", "description": "Required. Caller phone from Retell call metadata / inbound from_number. This links the call to GPS shared from the map phone button."},
                    "caller_name": {"type": "string", "description": "Caller name if already provided"},
                    "problem_description": {"type": "string", "description": "Brief description of the problem if already known"},
                    "problem_type": {"type": "string", "description": "Normalized problem type if known"},
                    "vehicle_type": {"type": "string", "description": "Vehicle type if already known"},
                    "city": {"type": "string", "description": "City if already known"},
                    "state": {"type": "string", "description": "State if already known"}
                },
                "required": ["source", "caller_phone"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-dispatch-session-status",
            "name": "get_dispatch_session_status",
            "description": "Poll the durable dispatch session created by create_dispatch_session. Use this every 8-10 seconds while checking for pre-shared GPS or mechanic matching progress. Speak only the returned say field and verified best_match fields.",
            "url": f"{BACKEND_URL}/api/dispatch/session-status",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "dispatch_session_id": {"type": "string", "description": "dispatch_session_id returned by create_dispatch_session"}
                },
                "required": ["dispatch_session_id"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-create-sr",
            "name": "create_service_request",
            "description": "Create the backend dispatch/manual-dispatch record after match_mechanic returns a useful match and the caller wants to proceed, or after automatic matching escalates to manual dispatch. Do not call before mechanic matching.",
            "url": f"{BACKEND_URL}/api/calls/create-service-request",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "retell_call_id":      {"type": "string", "description": "Retell call ID"},
                    "direction":           {"type": "string", "description": "inbound or outbound"},
                    "language":            {"type": "string", "description": "BCP-47 language code"},
                    "driver_safe":         {"type": "boolean", "description": "Is the driver safe and off the roadway?"},
                    "driver_name":         {"type": "string",  "description": "Driver's full name"},
                    "company_name":        {"type": "string",  "description": "Trucking company name if provided"},
                    "truck_type":          {"type": "string",  "description": "tractor|box_truck|straight_truck|bus|rv|pickup_hotshot|other"},
                    "trailer_type":        {"type": "string",  "description": "dry_van|reefer|flatbed|step_deck|tanker|lowboy|container_chassis|none|other"},
                    "loaded_status":       {"type": "string",  "description": "loaded|empty|bobtail|unknown"},
                    "problem_type":        {"type": "string",  "description": "tire|coolant_leak|no_start|dead_battery|locked_brakes|air_leak|fuel_issue|reefer_issue|derate|overheating|regen_issue|electrical|accident_damage|other"},
                    "problem_description": {"type": "string",  "description": "Detailed description of the problem"},
                    "fault_codes":         {"type": "array", "items": {"type": "string"}, "description": "Any fault/error codes mentioned"},
                    "caller_phone":        {"type": "string",  "description": "Caller's phone from Retell if available"},
                },
                "required": ["retell_call_id", "driver_safe", "driver_name", "problem_type", "problem_description"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-match-mechanic",
            "name": "match_mechanic",
            "description": "Search and rank Roadcall mechanics by GPS/city, problem type, vehicle type, mobile service, 24/7 availability, service radius, and priority score. Always pass callerPhone from Retell metadata. If the backend has map-shared GPS for that phone, it will use GPS even if city/state args are also present. Only search a caller-stated city instead when the caller explicitly asks to use that city instead of shared GPS. Do not invent results outside this tool response.",
            "url": f"{BACKEND_URL}/api/roadside/match-mechanic",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Latest caller message or concise summary"},
                    "transcript": {"type": "string", "description": "Conversation transcript so far, if available"},
                    "city": {"type": "string", "description": "Caller city if known"},
                    "state": {"type": "string", "description": "Caller state if known"},
                    "latitude": {"type": "number", "description": "Caller latitude if known"},
                    "longitude": {"type": "number", "description": "Caller longitude if known"},
                    "location": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "state": {"type": "string"},
                            "road": {"type": "string"},
                            "landmark": {"type": "string"},
                            "latitude": {"type": "number"},
                            "longitude": {"type": "number"},
                        },
                    },
                    "vehicleType": {"type": "string", "description": "Required if known before matching. Vehicle category: car/light-duty, pickup, box truck, semi/heavy-duty, trailer, RV, or fleet vehicle."},
                    "problemType": {"type": "string", "description": "Problem type, e.g. tire repair, engine, battery, fuel, towing"},
                    "callerPhone": {"type": "string", "description": "Caller's phone from Retell call metadata if available"},
                    "callbackNumber": {"type": "string", "description": "Callback/SMS number if already collected"},
                    "limit": {"type": "integer", "description": "Always return up to 3 local mechanics; the response also includes one majorVendor when available."},
                },
                "required": ["message"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-dispatch-status",
            "name": "get_dispatch_status",
            "description": "Poll the backend for current matching, payment, mechanic, ETA, and dispatch status. Call this every 8-10 seconds while waiting for a mechanic match. Only speak confirmed backend data.",
            "url": f"{BACKEND_URL}/api/dispatch/status",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "service_request_id": {"type": "string", "description": "The service_request_id to check status for"}
                },
                "required": ["service_request_id"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-payment-req",
            "name": "request_payment",
            "description": "Ask the backend to create a Stripe payment authorization and send a secure payment link by SMS. Never collect card details by voice.",
            "url": f"{BACKEND_URL}/api/payment/request",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "service_request_id": {"type": "string", "description": "The service_request_id"},
                    "reason":             {"type": "string", "description": "diagnostic_fee|service_authorization|deposit"},
                    "sms_template_id":    {"type": "string", "description": "Always 'payment_authorization'"}
                },
                "required": ["service_request_id"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-dispatch-confirm",
            "name": "confirm_dispatch",
            "description": "Finalize mechanic acceptance and confirm dispatch. Call this when backend status is mechanic_confirmed or payment_authorized. Optionally sends a tracking SMS to the driver.",
            "url": f"{BACKEND_URL}/api/dispatch/confirm",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "service_request_id": {"type": "string", "description": "The service_request_id"},
                    "send_tracking_sms":  {"type": "boolean", "description": "Whether to send a tracking link by SMS"},
                    "sms_template_id":    {"type": "string", "description": "Always 'tracking_link'"}
                },
                "required": ["service_request_id"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-warm-transfer",
            "name": "initiate_warm_transfer",
            "description": "Request backend approval for a warm transfer to the confirmed mechanic or human dispatcher. Only call this if the driver requests direct coordination AND dispatch status is confirmed.",
            "url": f"{BACKEND_URL}/api/transfer/warm",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "service_request_id":         {"type": "string", "description": "The service_request_id"},
                    "driver_requested_transfer":  {"type": "boolean", "description": "Whether the driver asked for direct connection"},
                    "reason":                     {"type": "string", "description": "driver_coordination|mechanic_needs_details|dispatcher_escalation"}
                },
                "required": ["service_request_id"]
            }
        }
    ],

    "nodes": [
        # ── 1. Start: one-time greeting ───────────────────
        {
            "id": "start-node",
            "type": "conversation",
            "name": "One-Time Greeting",
            "display_position": {"x": 100, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Speak exactly once: 'Thanks for calling Roadcall. This is Sandy. Who am I speaking with?'\n"
                    "Then stay silent and wait for real caller speech. Do not answer false noise, silence, or background audio. Do not repeat the greeting. Do not ask what they need yet in this node. Do not mention any website, link, text message, or location code. After the caller gives their name, route to Search Intake unless they mentioned injury, fire, danger, or 911."
                )
            },
            "edges": [
                {
                    "id": "edge-name-collected",
                    "transition_condition": {"type": "prompt", "prompt": "Caller provided their name, or declined to provide a name but still needs roadside help"},
                    "destination_node_id": "node-intake"
                },
                {
                    "id": "edge-emergency",
                    "transition_condition": {"type": "prompt", "prompt": "Driver mentions injuries, fire, danger, or needs 911 / emergency services"},
                    "destination_node_id": "node-end-emergency"
                }
            ]
        },

        # ── 2. Search intake without repeating greeting ──
        {
            "id": "node-intake",
            "type": "conversation",
            "name": "Search Intake",
            "display_position": {"x": 400, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Do not repeat the welcome message. Maintain the call facts ledger. Do not ask what is wrong until you have first created/read the dispatch session and handled the shared-location confirmation below.\n"
                    "Before asking the issue, call create_dispatch_session if it has not already been called. Pass caller_phone from call metadata when available plus caller_name and every known ledger fact. Store dispatch_session_id only; do not speak any location code, URL, link, or website instruction.\n"
                    "Immediately call get_dispatch_session_status. If location_captured is true, speak the returned location confirmation naturally, for example: 'I see your shared location near [address or city]. Is that correct?' Wait for the caller's yes/no answer before asking what is wrong.\n"
                    "If the caller confirms the shared location, ask exactly: 'What can I help you with today?' If the caller says the map location is wrong, ask for city and nearest highway or exit.\n"
                    "Use the pre-shared GPS from the Roadcall map phone button when the backend has it. Collect ONLY the missing search fact, one question at a time. Before asking, scan the full transcript and ledger; if the caller already gave the answer, use it and move to the next missing fact:\n"
                    "- If city/state missing and GPS has not arrived yet: 'What city and state are you in?'\n"
                    "- If state missing and city was already given: 'What state is that in?'\n"
                    "- If vehicle type missing and no vehicle was already given: 'What type of vehicle is it — car, pickup, box truck, semi, trailer, RV, or fleet vehicle?'\n"
                    "If a fact was already provided but may have been misheard, confirm it once with yes/no phrasing instead of re-asking the original question.\n"
                    "Do not ask road, exit, GPS, callback, company, payment, insurance, license plate, or address before matching.\n"
                    "If dispatch_session_id is known, poll get_dispatch_session_status every 8 to 10 seconds while you continue intake. Speak only the returned say field if it is useful and does not repeat a question already answered."
                )
            },
            "edges": [
                {
                    "id": "edge-intake-location-received",
                    "transition_condition": {"type": "prompt", "prompt": "get_dispatch_session_status says location_captured is true, status is matching or matched, or best_match is present"},
                    "destination_node_id": "node-dispatch-search"
                },
                {
                    "id": "edge-intake-have-search-info",
                    "transition_condition": {"type": "prompt", "prompt": "Caller has stated a city, a state (or US state implied by city), a problem type, and a vehicle type."},
                    "destination_node_id": "node-call-match-mechanic"
                }
            ]
        },

        # ── 2b. Function Node: actually invoke match_mechanic ──
        {
            "id": "node-call-match-mechanic",
            "type": "function",
            "name": "Call match_mechanic",
            "display_position": {"x": 550, "y": 300},
            "tool_id": "tool-roadcall-match-mechanic",
            "tool_type": "local",
            "wait_for_result": True,
            "speak_during_execution": True,
            "instruction": {
                "type": "prompt",
                "text": "Briefly say: 'I'm checking Roadcall's live mechanic availability near [city].' Keep it to one short sentence. Do not name any mechanic yet."
            },
            "edges": [
                {
                    "id": "edge-match-found",
                    "transition_condition": {"type": "prompt", "prompt": "match_mechanic tool result contains at least one entry in matches (matches.length >= 1)"},
                    "destination_node_id": "node-match-results"
                },
                {
                    "id": "edge-match-needs-more",
                    "transition_condition": {"type": "prompt", "prompt": "match_mechanic tool result has needsMoreInfo true or status needs_more_info"},
                    "destination_node_id": "node-match-more-info"
                },
                {
                    "id": "edge-match-none",
                    "transition_condition": {"type": "prompt", "prompt": "match_mechanic tool result has no matches, status manual_dispatch_required, fallbackEscalation true, or the tool errored or timed out"},
                    "destination_node_id": "node-no-mechanic"
                }
            ]
        },

        {
            "id": "node-match-more-info",
            "type": "conversation",
            "name": "Ask Missing Match Info",
            "display_position": {"x": 600, "y": 120},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Ask only the missing field from match_mechanic.message, but first compare the missing field with the call facts ledger.\n"
                    "If the requested field is already in the ledger, do not ask the caller; immediately call match_mechanic again with the ledger values.\n"
                    "If location is truly missing, ask: 'What city and state are you in?'\n"
                    "If state is truly missing, ask: 'What state is that in?'\n"
                    "If problemType is truly missing, ask: 'What problem are you having — tire, engine, battery, fuel, towing, or something else?'\n"
                    "If vehicleType is truly missing, ask: 'What type of vehicle is it — car, pickup, box truck, semi, trailer, RV, or fleet vehicle?'\n"
                    "After the caller answers, store the answer in the ledger and call match_mechanic again with all known values. Always include callerPhone so the backend can use map-shared GPS when available."
                )
            },
            "edges": [
                {
                    "id": "edge-more-info-collected",
                    "transition_condition": {"type": "prompt", "prompt": "Caller answered the missing city, state, road, exit, landmark, problem, or vehicle type question"},
                    "destination_node_id": "node-intake"
                }
            ]
        },

        # ── 3. Match Result Offer ─────────────────────────
        {
            "id": "node-match-results",
            "type": "conversation",
            "name": "Mechanic Match Results",
            "display_position": {"x": 700, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Use the latest match_mechanic tool response only. Prefer speaking match_mechanic.message verbatim when it is present, because the backend already decides whether this is a city-level options list or an exact/radius match.\n"
                    "If the response includes several matches, mention up to three returned businessName values exactly; do not invent names and do not force matches[0].\n"
                    "Do NOT read phone numbers for every option. Read a phone number only if the caller asks for a number or chooses a specific mechanic.\n"
                    "After listing options, ask exactly one short next-step question: 'Do you want me to start with one of these options or keep searching from your shared location?'\n"
                    "If the caller gives a different city and explicitly asks to use it instead of their shared GPS, go back to match intake and call match_mechanic again with that city.\n"
                    "If the caller wants Roadcall to continue dispatch, move to post-match dispatch intake.\n"
                    "If the caller chooses a mechanic by name or option number, use that match context and move to post-match dispatch intake.\n"
                    "FORBIDDEN: inventing or guessing a mechanic name, phone, address, or ETA. Only speak businessName, phone, city, address values that appeared verbatim in the latest match_mechanic response.\n"
                    "Never claim a mechanic is dispatched, confirmed, nearby, or en route unless backend dispatch status explicitly says so."
                )
            },
            "edges": [
                {
                    "id": "edge-read-number-again",
                    "transition_condition": {"type": "prompt", "prompt": "Caller asks for the mechanic phone number again or wants to call the mechanic themselves"},
                    "destination_node_id": "node-read-mechanic-phone"
                },
                {
                    "id": "edge-connect",
                    "transition_condition": {"type": "prompt", "prompt": "Caller wants Roadcall to create the dispatch request, send GPS link, or continue helping"},
                    "destination_node_id": "node-post-match-intake"
                },
                {
                    "id": "edge-not-proceeding",
                    "transition_condition": {"type": "prompt", "prompt": "Caller does not want to proceed"},
                    "destination_node_id": "node-end-success"
                }
            ]
        },

        {
            "id": "node-read-mechanic-phone",
            "type": "conversation",
            "name": "Read Mechanic Phone",
            "display_position": {"x": 850, "y": 120},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Read the phone for the mechanic the caller chose. If they did not choose one, ask which option they want first.\n"
                    "Use only businessName and phone values from the latest match_mechanic response; do not invent or guess.\n"
                    "Then ask: 'Do you want me to also create a Roadcall dispatch request using your shared location?'\n"
                    "Do not end unless the caller explicitly says they are all set or no longer need help."
                )
            },
            "edges": [
                {
                    "id": "edge-phone-dispatch-request",
                    "transition_condition": {"type": "prompt", "prompt": "Caller wants Roadcall dispatch request or GPS text after hearing mechanic phone"},
                    "destination_node_id": "node-post-match-intake"
                },
                {
                    "id": "edge-phone-done",
                    "transition_condition": {"type": "prompt", "prompt": "Caller explicitly says they are all set, will call the mechanic themselves, or no longer need help"},
                    "destination_node_id": "node-end-success"
                }
            ]
        },

        # ── 4. Post-Match Dispatch Intake ─────────────────
        {
            "id": "node-post-match-intake",
            "type": "conversation",
            "name": "Post-Match Dispatch Intake",
            "display_position": {"x": 900, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Now collect only what is required to create the dispatch record, one question at a time. Use the ledger first; do not re-ask for name, problem, vehicle type, city, state, callback, or selected mechanic if already known:\n"
                    "This node is used after a mechanic match OR after automatic matching escalates to manual dispatch.\n"
                    "1. If call.caller_phone is available, pass it silently as caller_phone. Use the existing location session.\n"
                    "2. If driver_name is still missing: 'What name should I put on the request?'\n"
                    "3. If vehicle type is still missing: 'What are you driving — semi, box truck, trailer, RV, or something else?'\n"
                    "Do not ask for email, payment, company, insurance, license plate, or other unnecessary details.\n"
                    "Then call create_service_request using the already captured location/problem/match context."
                )
            },
            "edges": [
                {
                    "id": "edge-service-created",
                    "transition_condition": {"type": "prompt", "prompt": "create_service_request tool has been called successfully and returned a service_request_id"},
                    "destination_node_id": "node-location"
                },
                {
                    "id": "edge-service-create-fail",
                    "transition_condition": {"type": "prompt", "prompt": "create_service_request returned ok=false or an error occurred"},
                    "destination_node_id": "node-no-mechanic"
                }
            ]
        },

        # ── 5. Location Request ───────────────────────────
        {
            "id": "node-location",
            "type": "conversation",
            "name": "Location Request",
            "display_position": {"x": 700, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Location check for this call:\n"
                    "1. If get_dispatch_session_status has not been called yet and dispatch_session_id is known, call it now.\n"
                    "2. If the backend confirms GPS, say: 'Got it, I have your location.' Then move straight to mechanic search.\n"
                    "3. If no GPS is on file, ask verbally for highway or interstate, mile marker or nearest exit, city and state, and a nearby truck stop or landmark. Ask one short question at a time and continue with whatever the caller can provide.\n"
                    "Do not mention websites, browser pages, links, text messages, codes, or any alternate location-sharing flow. Do not ask for the caller's phone number. Once you have a usable location from the backend or from what the caller says, move to dispatch search."
                )
            },
            "edges": [
                {
                    "id": "edge-location-done",
                    "transition_condition": {"type": "prompt", "prompt": "Location link sent or manual location collected — ready to search for mechanics"},
                    "destination_node_id": "node-dispatch-search"
                }
            ]
        },

        # ── 4. Dispatch Search / Polling ──────────────────
        {
            "id": "node-dispatch-search",
            "type": "conversation",
            "name": "Dispatch Search and Polling",
            "display_position": {"x": 1000, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Tell the driver: 'I'm searching for a qualified heavy-duty mechanic near your location now. Hang tight.'\n"
                    "If dispatch_session_id is available, call get_dispatch_session_status first. If only service_request_id is available, call get_dispatch_status with the service_request_id.\n"
                    "While polling, do not go silent long enough for the call to end. Use brief reassurance every 8-10 seconds — vary the phrasing:\n"
                    "  - 'Still searching. I'm looking for someone who handles your specific issue.'\n"
                    "  - 'I'm checking technician availability in your area.'\n"
                    "  - 'Thanks for your patience. I haven't found a confirmed match yet.'\n\n"
                    "When get_dispatch_session_status returns, speak the say field exactly unless it asks for missing information; use best_match only if present. When get_dispatch_status returns:\n"
                    "- status 'intake_created', 'location_requested', or 'matching': Keep the caller on the line and continue polling with brief reassurance.\n"
                    "- status 'matched' or 'mechanic_confirmed': Announce the mechanic and ETA (only speak confirmed backend data), then move to payment or confirm.\n"
                    "- status 'payment_required': Move to payment node.\n"
                    "- status 'dispatched': Move to confirmed node.\n"
                    "- status 'no_mechanic_found' or 'search_continues' after multiple polls: Move to no-mechanic node.\n"
                    "- status 'mechanic_cancelled': Apologize briefly, restart search.\n"
                    "- status 'failed', tool timeout, or repeated polling error: Say you are escalating for manual dispatch, then move to no-mechanic/manual dispatch. Do not end the call.\n\n"
                    "Do NOT mention ETAs, mechanic names, or dispatch confirmation unless backend returned them explicitly."
                )
            },
            "edges": [
                {
                    "id": "edge-keep-polling",
                    "transition_condition": {"type": "prompt", "prompt": "get_dispatch_status returned service_status intake_created, location_requested, matching, or search still in progress"},
                    "destination_node_id": "node-search-reassure"
                },
                {
                    "id": "edge-matched",
                    "transition_condition": {"type": "prompt", "prompt": "get_dispatch_status returned service_status matched, mechanic_confirmed, or payment_authorized"},
                    "destination_node_id": "node-payment-check"
                },
                {
                    "id": "edge-dispatched",
                    "transition_condition": {"type": "prompt", "prompt": "get_dispatch_status returned service_status dispatched"},
                    "destination_node_id": "node-confirmed"
                },
                {
                    "id": "edge-no-mechanic",
                    "transition_condition": {"type": "prompt", "prompt": "get_dispatch_status returned no_mechanic_found or search_continues after several attempts"},
                    "destination_node_id": "node-no-mechanic"
                },
                {
                    "id": "edge-search-fail",
                    "transition_condition": {"type": "prompt", "prompt": "get_dispatch_status returned failed or repeated errors"},
                    "destination_node_id": "node-no-mechanic"
                }
            ]
        },

        {
            "id": "node-search-reassure",
            "type": "conversation",
            "name": "Search Reassurance",
            "display_position": {"x": 1180, "y": 180},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Keep the caller on the line. Say one short reassurance such as: 'Still checking — I’m looking for someone who can handle your issue.'\n"
                    "Do not end the call. Return to dispatch search and poll again."
                )
            },
            "edges": [
                {
                    "id": "edge-reassure-continue-search",
                    "transition_condition": {"type": "prompt", "prompt": "Short reassurance spoken and ready to poll dispatch status again"},
                    "destination_node_id": "node-dispatch-search"
                }
            ]
        },

        {
            "id": "node-payment-check",
            "type": "conversation",
            "name": "Payment Authorization",
            "display_position": {"x": 1000, "y": 550},
            "instruction": {
                "type": "prompt",
                "text": (
                    "If the backend returned payment_required=true and payment_authorization_status is NOT 'authorized':\n"
                    "  Say: 'I found a provider — [mechanic_company] with an ETA of approximately [eta_text]. Before I can finalize, I need a payment authorization. I'm texting you a secure link now — please do not read any card numbers to me over the phone.'\n"
                    "  Use the current call record for payment authorization if required.\n"
                    "  Then poll get_dispatch_status every 10 seconds until authorization_status is 'authorized'.\n"
                    "  While waiting: 'Waiting on your payment authorization. Just tap the link and complete it there.'\n"
                    "  If authorization_status is 'declined': Say the authorization didn't go through, offer to resend.\n\n"
                    "If payment is not required OR already authorized:\n"
                    "  Move directly to dispatch confirmation."
                )
            },
            "edges": [
                {
                    "id": "edge-payment-done",
                    "transition_condition": {"type": "prompt", "prompt": "Payment is authorized or not required — ready to confirm dispatch"},
                    "destination_node_id": "node-confirm"
                },
                {
                    "id": "edge-payment-declined",
                    "transition_condition": {"type": "prompt", "prompt": "Payment authorization was declined and driver cannot proceed"},
                    "destination_node_id": "node-end-payment-pending"
                }
            ]
        },

        # ── 6. Confirm Dispatch ────────────────────────────
        {
            "id": "node-confirm",
            "type": "conversation",
            "name": "Confirm Dispatch",
            "display_position": {"x": 1300, "y": 400},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Call confirm_dispatch with service_request_id and send_tracking_sms=true.\n"
                    "After the tool returns:\n"
                    "  Say: 'You're confirmed. [mechanic_company] has accepted the job. ETA is [eta_text]. I'm sending a tracking link by text — you can watch their progress from there.'\n"
                    "  Tell the driver: stay in a safe location, keep their phone available, the mechanic may call for final directions.\n"
                    "If the driver asks to speak directly with the mechanic, move to warm transfer.\n"
                    "Otherwise close the call."
                )
            },
            "edges": [
                {
                    "id": "edge-confirm-transfer",
                    "transition_condition": {"type": "prompt", "prompt": "Driver requests to speak directly with the mechanic"},
                    "destination_node_id": "node-warm-transfer"
                },
                {
                    "id": "edge-confirm-done",
                    "transition_condition": {"type": "prompt", "prompt": "Dispatch confirmed and driver has no more questions"},
                    "destination_node_id": "node-confirmed"
                }
            ]
        },

        # ── 7. Already Dispatched ─────────────────────────
        {
            "id": "node-confirmed",
            "type": "conversation",
            "name": "Dispatch Confirmed Close",
            "display_position": {"x": 1600, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Tell the driver:\n"
                    "'You're all set with Roadcall.ai. Keep your phone close, stay safe, and use the tracking link for live updates. Call us back if anything changes.'\n"
                    "Answer any remaining questions briefly, then end the call."
                )
            },
            "edges": [
                {
                    "id": "edge-confirmed-end",
                    "transition_condition": {"type": "prompt", "prompt": "Driver is satisfied and has no more questions"},
                    "destination_node_id": "node-end-success"
                }
            ]
        },

        # ── 8. Warm Transfer ──────────────────────────────
        {
            "id": "node-warm-transfer",
            "type": "conversation",
            "name": "Warm Transfer",
            "display_position": {"x": 1600, "y": 550},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Call initiate_warm_transfer with service_request_id and driver_requested_transfer=true.\n"
                    "If transfer_approved=true and transfer_phone is present:\n"
                    "  Say: 'I'll connect you now. I'll brief them first so you don't have to repeat your breakdown details.'\n"
                    "  Then transfer the call to transfer_phone using the whisper_text from the response.\n"
                    "If transfer_approved=false:\n"
                    "  Say: 'The mechanic has your details. They'll call if they need final directions.'\n"
                    "  Move to success close."
                )
            },
            "edges": [
                {
                    "id": "edge-transfer-end",
                    "transition_condition": {"type": "prompt", "prompt": "Transfer completed or not approved"},
                    "destination_node_id": "node-end-success"
                }
            ]
        },

        # ── 9. No Mechanic Found ──────────────────────────
        {
            "id": "node-no-mechanic",
            "type": "conversation",
            "name": "No Mechanic Found",
            "display_position": {"x": 1300, "y": 100},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Say: 'I don't have a confirmed heavy-duty mechanic available yet for your location and issue. "
                    "I'm escalating this for manual dispatch and creating the request now.'\n"
                    "If match_mechanic failed or timed out, say: 'I'm having trouble checking live availability, but I can still create a manual dispatch request.'\n"
                    "Do not end the call here unless the caller explicitly says they no longer need help.\n"
                    "Collect callback/name only as needed and create the manual dispatch request.\n"
                    "If the situation becomes unsafe: direct them to 911."
                )
            },
            "edges": [
                {
                    "id": "edge-no-mech-manual-dispatch",
                    "transition_condition": {"type": "prompt", "prompt": "Driver still needs help or accepts manual dispatch"},
                    "destination_node_id": "node-post-match-intake"
                },
                {
                    "id": "edge-no-mech-no-help-needed",
                    "transition_condition": {"type": "prompt", "prompt": "Driver explicitly says they no longer need help"},
                    "destination_node_id": "node-end-success"
                }
            ]
        },

        # ── End Nodes ─────────────────────────────────────
        {
            "id": "node-end-success",
            "type": "end",
            "name": "Successful Close",
            "display_position": {"x": 1900, "y": 300},
            "instruction": {
                "type": "static_text",
                "text": "Thanks for calling Roadcall.ai. Stay safe on the roadway. Goodbye."
            }
        },
        {
            "id": "node-end-callback",
            "type": "end",
            "name": "Callback Close",
            "display_position": {"x": 1900, "y": 100},
            "instruction": {
                "type": "prompt",
                "text": "Tell the driver the search stays active and end the call professionally."
            }
        },
        {
            "id": "node-end-emergency",
            "type": "end",
            "name": "Emergency Close",
            "display_position": {"x": 100, "y": 100},
            "instruction": {
                "type": "static_text",
                "text": "Please call 911 now. Your safety is the priority. Goodbye."
            }
        },
        {
            "id": "node-end-payment-pending",
            "type": "end",
            "name": "Payment Pending Close",
            "display_position": {"x": 1900, "y": 550},
            "instruction": {
                "type": "prompt",
                "text": "Tell the driver the request is pending payment authorization. Once the secure link is completed, dispatch will continue."
            }
        }
    ],

    "start_node_id": "start-node"
}

if EXPORT_JSON_PATH:
    export_path = Path(EXPORT_JSON_PATH)
    if not export_path.is_absolute():
        export_path = Path(__file__).parent.parent / export_path
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(FLOW, indent=2, ensure_ascii=False) + "\n")
    print(f"✅ Exported Sandy conversation flow JSON: {export_path}")
    sys.exit(0)

if EXISTING_FLOW_ID:
    print(f"Updating existing Roadcall.ai conversational flow: {EXISTING_FLOW_ID}")
    flow_resp = retell("PATCH", f"/update-conversation-flow/{EXISTING_FLOW_ID}", FLOW)
    flow_id = flow_resp.get("conversation_flow_id", EXISTING_FLOW_ID)
    print(f"✅ Conversation flow updated: {flow_id}")
else:
    print("Creating Roadcall.ai conversational flow...")
    flow_resp = retell("POST", "/create-conversation-flow", FLOW)
    flow_id = flow_resp["conversation_flow_id"]
    print(f"✅ Conversation flow created: {flow_id}")

# ── Create or update the Sandy agent ──────────────────────
agent_body = {
    "agent_name": "Sandy — Roadcall.ai Dispatcher",
    "response_engine": {
        "type": "conversation-flow",
        "conversation_flow_id": flow_id
    },
    "voice_id": "11labs-Lily",
    "language": "en-US",
    # Pacing: lower interruption sensitivity = more patient, won't cut driver off mid-sentence.
    # voice_speed < 1.0 slows delivery; responsiveness < 1.0 lets her wait a beat before replying.
    "interruption_sensitivity": 0.2,
    "responsiveness": 0.55,
    "voice_speed": 0.93,
    "voice_temperature": 0.75,
    "begin_message_delay_ms": 600,
    "denoising_mode": "noise-and-background-speech-cancellation",
    "enable_backchannel": True,
    "backchannel_frequency": 0.5,
    "backchannel_words": ["okay", "got it", "uh huh", "right"],
    "max_call_duration_ms": 1800000,
    "end_call_after_silence_ms": 120000,
    "boosted_keywords": [
        "roadside", "mechanic", "towing", "tractor", "trailer",
        "tire", "coolant", "no-start", "derate", "air leak",
        "roadcall", "dispatch", "shared location", "GPS", "nearest mechanic",
    ],
    "normalize_for_speech": True,
}
if EXISTING_AGENT_ID:
    print(f"\nUpdating existing Sandy agent: {EXISTING_AGENT_ID}")
    agent_resp = retell("PATCH", f"/update-agent/{EXISTING_AGENT_ID}", agent_body)
    agent_id = agent_resp.get("agent_id", EXISTING_AGENT_ID)
    print(f"✅ Agent updated: {agent_id}")
else:
    print("\nCreating Sandy agent with conversational flow...")
    agent_resp = retell("POST", "/create-agent", agent_body)
    agent_id = agent_resp["agent_id"]
    print(f"✅ Agent created: {agent_id}")
print(f"\n{'='*60}")
print(f"  Conversation Flow ID : {flow_id}")
print(f"  Agent ID             : {agent_id}")
print(f"  Agent Name           : Sandy — Roadcall.ai Dispatcher")
print(f"  Backend URL          : {BACKEND_URL}")
print(f"{'='*60}")
print("\nNext steps:")
if EXISTING_AGENT_ID:
    print("  1. Call the Roadcall number and verify the opening line is warm and asks who is speaking")
    print("  2. If it still sounds old, confirm the phone number is assigned to this agent ID in Retell")
else:
    print("  1. Go to Retell dashboard and assign this new agent to your phone number")
    print(f"  2. Update RETELL_AGENT_ID={agent_id} in your .env / DO env if needed")
print(f"  3. Backend URL used by tools: {BACKEND_URL}")
print("  4. Ensure RETELL_BACKEND_WEBHOOK_TOKEN in Retell tools matches the backend env var")
