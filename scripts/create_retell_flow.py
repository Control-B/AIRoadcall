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
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

RETELL_KEY    = os.environ["RETELL_API_KEY"]
WEBHOOK_TOKEN = os.environ.get("RETELL_BACKEND_WEBHOOK_TOKEN", "local-dev-retell-token")
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
    "tool_call_strict_mode": False,

    "global_prompt": "\n".join([
        "You are Sandy, the Roadcall.ai AI dispatcher for heavy-duty trucking roadside assistance.",
        "Your job: keep the driver calm, collect structured intake, trigger backend tools, speak backend status updates, and warm transfer only when backend approves.",
        "The backend handles GPS tokens, mechanic matching, ETA, Stripe payment authorization, dispatch records, tracking, and transcripts.",
        "NEVER claim a mechanic is dispatched, confirmed, or en route unless backend status explicitly says so.",
        "Use concise dispatcher language. Ask one or two questions at a time. Confirm critical details before moving on.",
        "If the driver is unsafe, injured, or needs emergency response, direct them to call 911 immediately.",
        "Detect the driver's language automatically and continue in that language.",
        "Use trucking terms naturally: reefer, tractor, trailer, bobtail, steer tire, drive tire, coolant leak, no-start, derate, air leak, locked brakes.",
        "When backend work is in progress, reassure the driver briefly — never describe APIs, webhooks, tokens, or database details.",
        "Do not collect raw card details. Send secure payment links only.",
        f"Backend base URL: {BACKEND_URL}",
    ]),

    "tools": [
        {
            "type": "custom",
            "tool_id": "tool-roadcall-create-sr",
            "name": "create_service_request",
            "description": "Create the backend dispatch record after confirming driver safety and collecting driver name, callback number, truck/trailer type, and problem details.",
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
                    "callback_number":     {"type": "string",  "description": "Driver's callback phone in E.164"},
                    "company_name":        {"type": "string",  "description": "Trucking company name if provided"},
                    "truck_type":          {"type": "string",  "description": "tractor|box_truck|straight_truck|bus|rv|pickup_hotshot|other"},
                    "trailer_type":        {"type": "string",  "description": "dry_van|reefer|flatbed|step_deck|tanker|lowboy|container_chassis|none|other"},
                    "loaded_status":       {"type": "string",  "description": "loaded|empty|bobtail|unknown"},
                    "problem_type":        {"type": "string",  "description": "tire|coolant_leak|no_start|dead_battery|locked_brakes|air_leak|fuel_issue|reefer_issue|derate|overheating|regen_issue|electrical|accident_damage|other"},
                    "problem_description": {"type": "string",  "description": "Detailed description of the problem"},
                    "fault_codes":         {"type": "array", "items": {"type": "string"}, "description": "Any fault/error codes mentioned"},
                    "caller_phone":        {"type": "string",  "description": "Caller's phone from Retell if available"},
                },
                "required": ["retell_call_id", "driver_safe", "driver_name", "callback_number", "problem_type", "problem_description"]
            }
        },
        {
            "type": "custom",
            "tool_id": "tool-roadcall-request-loc",
            "name": "request_location",
            "description": "Ask backend to generate a secure GPS location link and send it by SMS to the driver. Use this after creating the service request. If driver cannot receive SMS, pass manual_location_details instead.",
            "url": f"{BACKEND_URL}/api/location/request",
            "method": "POST",
            "headers": {"Authorization": f"Bearer {WEBHOOK_TOKEN}"},
            "parameters": {
                "type": "object",
                "properties": {
                    "service_request_id": {"type": "string", "description": "The service_request_id returned by create_service_request"},
                    "callback_number":    {"type": "string", "description": "Driver's phone number to SMS the location link"},
                    "preferred_channel":  {"type": "string", "description": "Always 'sms'"},
                    "sms_template_id":    {"type": "string", "description": "Always 'location_request'"},
                    "manual_location_details": {
                        "type": "object",
                        "description": "Only fill if SMS failed — collect highway, mile marker, exit, city, state, truck stop, landmark, direction",
                        "properties": {
                            "interstate_or_highway": {"type": "string"},
                            "mile_marker":           {"type": "string"},
                            "nearest_exit":          {"type": "string"},
                            "city":                  {"type": "string"},
                            "state":                 {"type": "string"},
                            "truck_stop":            {"type": "string"},
                            "landmark":              {"type": "string"},
                            "direction_of_travel":   {"type": "string"}
                        }
                    }
                },
                "required": ["service_request_id", "callback_number"]
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
                    "callback_number":    {"type": "string", "description": "Driver phone to SMS the payment link"},
                    "reason":             {"type": "string", "description": "diagnostic_fee|service_authorization|deposit"},
                    "sms_template_id":    {"type": "string", "description": "Always 'payment_authorization'"}
                },
                "required": ["service_request_id", "callback_number"]
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
        # ── 1. Start: Greeting + Safety ───────────────────
        {
            "id": "start-node",
            "type": "conversation",
            "name": "Greeting and Safety Check",
            "start_speaker": "agent",
            "display_position": {"x": 100, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Greet the driver professionally: 'Roadcall.ai, this is Sandy. Are you safe and off the roadway?'\n"
                    "If they say yes or seem safe, move to intake.\n"
                    "If they mention injuries, danger, fire, or need emergency services — tell them to call 911 immediately, then move to emergency end.\n"
                    "Keep it short — one sentence greeting, one safety question."
                )
            },
            "edges": [
                {
                    "id": "edge-safe",
                    "transition_condition": {"type": "prompt", "prompt": "Driver confirms they are safe or answers the intake questions"},
                    "destination_node_id": "node-intake"
                },
                {
                    "id": "edge-emergency",
                    "transition_condition": {"type": "prompt", "prompt": "Driver mentions injuries, fire, danger, or needs 911 / emergency services"},
                    "destination_node_id": "node-end-emergency"
                }
            ]
        },

        # ── 2. Driver + Equipment + Problem Intake ────────
        {
            "id": "node-intake",
            "type": "conversation",
            "name": "Driver and Problem Intake",
            "display_position": {"x": 400, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Collect the following information, asking 1-2 questions at a time and confirming before moving on:\n"
                    "1. Driver's first and last name\n"
                    "2. Best callback phone number (confirm it's a mobile number that can receive texts)\n"
                    "3. Trucking company name (optional — 'personal' is fine)\n"
                    "4. Truck type: tractor, box truck, straight truck, RV, pickup/hotshot, or other\n"
                    "5. Trailer type: dry van, reefer, flatbed, step deck, tanker, lowboy, none (bobtail), or other\n"
                    "6. Loaded or empty (or bobtail)\n"
                    "7. Problem type — use dispatch terms: tire, coolant leak, no-start, dead battery, locked brakes, air leak, fuel issue, reefer issue, derate, overheating, regen issue, electrical, accident damage, or other\n"
                    "8. Brief problem description — what exactly is happening?\n"
                    "9. Any fault codes or warning lights? (optional)\n\n"
                    "Once you have name, callback number, truck type, problem type, and description — call create_service_request immediately.\n"
                    "Pass retell_call_id from the call metadata, driver_safe=true, and all collected fields."
                )
            },
            "edges": [
                {
                    "id": "edge-intake-done",
                    "transition_condition": {"type": "prompt", "prompt": "create_service_request tool has been called successfully and returned a service_request_id"},
                    "destination_node_id": "node-location"
                },
                {
                    "id": "edge-intake-fail",
                    "transition_condition": {"type": "prompt", "prompt": "create_service_request returned ok=false or an error occurred"},
                    "destination_node_id": "node-end-callback"
                }
            ]
        },

        # ── 3. Location Request ───────────────────────────
        {
            "id": "node-location",
            "type": "conversation",
            "name": "Location Request",
            "display_position": {"x": 700, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Call request_location with the service_request_id and the driver's callback number.\n"
                    "After calling the tool:\n"
                    "- If location_status is 'sms_sent': Tell the driver: 'I just texted you a location link. Tap it and hit Allow so I can find mechanics near you. Takes about 10 seconds.'\n"
                    "- If location_status is 'sms_failed': Say the text couldn't go through and ask for their highway/interstate, mile marker or nearest exit, city and state, and any nearby truck stop or landmark.\n"
                    "  Then call request_location again with manual_location_details filled in.\n"
                    "Once location is sent or manually collected, move to dispatch search."
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
                    "Call get_dispatch_status with the service_request_id.\n"
                    "While polling, use brief reassurance every 8-10 seconds — vary the phrasing:\n"
                    "  - 'Still searching. I'm looking for someone who handles your specific issue.'\n"
                    "  - 'I'm checking technician availability in your area.'\n"
                    "  - 'Thanks for your patience. I haven't found a confirmed match yet.'\n\n"
                    "When get_dispatch_status returns:\n"
                    "- status 'matched' or 'mechanic_confirmed': Announce the mechanic and ETA (only speak confirmed backend data), then move to payment or confirm.\n"
                    "- status 'payment_required': Move to payment node.\n"
                    "- status 'dispatched': Move to confirmed node.\n"
                    "- status 'no_mechanic_found' or 'search_continues' after multiple polls: Move to no-mechanic node.\n"
                    "- status 'mechanic_cancelled': Apologize briefly, restart search.\n"
                    "- status 'failed': Move to backend failure end.\n\n"
                    "Do NOT mention ETAs, mechanic names, or dispatch confirmation unless backend returned them explicitly."
                )
            },
            "edges": [
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
                    "destination_node_id": "node-end-callback"
                }
            ]
        },

        # ── 5. Payment Check / Authorization ──────────────
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
                    "  Call request_payment with service_request_id and callback_number.\n"
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
                    "  Say: 'The mechanic has your details and callback number. They'll call if they need final directions.'\n"
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
                    "I'm keeping the search active and will call you back as soon as a qualified provider confirms.'\n"
                    "Ask if they want to stay on the line or prefer a callback.\n"
                    "If they want to wait, poll get_dispatch_status again.\n"
                    "If they prefer callback, end with callback close.\n"
                    "If the situation becomes unsafe: direct them to 911."
                )
            },
            "edges": [
                {
                    "id": "edge-no-mech-wait",
                    "transition_condition": {"type": "prompt", "prompt": "Driver wants to wait on the line — resume polling"},
                    "destination_node_id": "node-dispatch-search"
                },
                {
                    "id": "edge-no-mech-callback",
                    "transition_condition": {"type": "prompt", "prompt": "Driver accepts callback or wants to hang up"},
                    "destination_node_id": "node-end-callback"
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
                "text": "Stay safe on the roadway. Roadcall.ai has your dispatch confirmed. Goodbye."
            }
        },
        {
            "id": "node-end-callback",
            "type": "end",
            "name": "Callback Close",
            "display_position": {"x": 1900, "y": 100},
            "instruction": {
                "type": "prompt",
                "text": "Confirm the callback number, tell the driver the search stays active, and end the call professionally."
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
                "text": "Tell the driver the request is pending payment authorization. Once the secure link is completed, dispatch will continue. Provide the callback number for questions."
            }
        }
    ],

    "start_node_id": "start-node"
}

print("Creating Roadcall.ai conversational flow...")
flow_resp = retell("POST", "/create-conversation-flow", FLOW)
flow_id = flow_resp["conversation_flow_id"]
print(f"✅ Conversation flow created: {flow_id}")

# ── Create or update the Sandy agent ──────────────────────
print("\nCreating Sandy agent with conversational flow...")
agent_body = {
    "agent_name": "Sandy — Roadcall.ai Dispatcher",
    "response_engine": {
        "type": "conversation-flow",
        "conversation_flow_id": flow_id
    },
    "voice_id": "11labs-Lily",
    "language": "en-US",
    "interruption_sensitivity": 0.9,
    "enable_backchannel": True,
    "max_call_duration_ms": 1800000,
    "end_call_after_silence_ms": 30000,
    "boosted_keywords": [
        "roadside", "mechanic", "towing", "tractor", "trailer",
        "tire", "coolant", "no-start", "derate", "air leak"
    ],
    "normalize_for_speech": True,
}
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
print("  1. Go to Retell dashboard and assign this agent to your phone number")
print(f"  2. Set BACKEND_URL in Retell to your production URL (current: {BACKEND_URL})")
print("  3. Set RETELL_BACKEND_WEBHOOK_TOKEN in your DO app env vars")
print(f"  4. Update RETELL_AGENT_ID={agent_id} in your .env if needed")
