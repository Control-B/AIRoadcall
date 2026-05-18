#!/usr/bin/env python3
"""Create or update the Roadcall Shop AI Receptionist conversational flow + agent.

This is the THIRD Retell agent (alongside Sandy roadside + Fleet roadside).
It powers the per-tenant shop AI answering line:
  • greets the caller using the shop name
  • triages intent (new lead, appointment, existing customer, quote, emergency)
  • captures structured details via Roadcall backend tools
  • offers the shop's Cal.com booking link when present
  • optionally texts a follow-up

Per-tenant context (shop_name, tenant_id, calcom_calendar_url, etc.) is injected
into the agent's dynamic_variables at provisioning time by
``RetellProvisioningService.provision_agent`` when ``vertical="shops"``.

Reads from .env:
  RETELL_API_KEY                       (required)
  RETELL_BACKEND_WEBHOOK_TOKEN         (required; shared secret for tool auth)
  RETELL_BACKEND_URL or APP_BASE_URL   (required; public HTTPS, not localhost)
  RETELL_SHOP_AGENT_ID                 (optional; PATCH-updates existing agent)
  RETELL_SHOP_CONVERSATION_FLOW_ID     (optional; PATCH-updates existing flow)
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
EXISTING_AGENT_ID = os.environ.get("RETELL_SHOP_AGENT_ID", "").strip()
EXISTING_FLOW_ID = os.environ.get("RETELL_SHOP_CONVERSATION_FLOW_ID", "").strip()
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
    "You are the Roadcall AI receptionist for {{shop_name}}, an independent truck/auto repair shop.",
    "You are NOT a roadside dispatcher. You answer the shop's main line, qualify the caller, and either schedule them, capture a lead, or take a message.",
    "Always identify the business as {{shop_name}} when greeting and never as 'Roadcall'. Roadcall is the platform — the caller dialed {{shop_name}}.",
    "HARD RULE — KEEP IT SHORT: ask one question at a time. Get name and phone first, then intent, then the few details you need for that intent. No interrogation.",
    "Intents you handle: 1) NEW LEAD / first-time customer, 2) APPOINTMENT request, 3) QUOTE request, 4) EXISTING CUSTOMER status check, 5) MESSAGE for the shop, 6) EMERGENCY.",
    "EMERGENCY rule: if the caller mentions fire, injury, crash, or being stranded in an unsafe spot, tell them to hang up and call 911 immediately. Then offer to text them a roadside link after they are safe.",
    "Never invent appointment times, mechanic names, or part prices. Only speak facts returned by a tool.",
    "Always call save_lead exactly once per call after you have name + phone + intent. Then, if they asked for an appointment, call book_appointment. Just before ending the call, call save_call_summary with a one-paragraph summary.",
    "If the caller provides a phone number for follow-up and asks for a confirmation, you may call send_sms_followup with a short, friendly message. Do not spam — at most one SMS per call.",
    "ALWAYS pass tenant_id={{tenant_id}} to every tool call.",
    "Voice style: warm, calm, professional. Speak like a friendly front-desk human. Half-second pause between sentences. Never read URLs character-by-character — say 'I'll text you the link.'",
    f"Backend base URL: {BACKEND_URL}",
])

TOOLS = [
    {
        "type": "custom",
        "tool_id": "tool-shopai-save-lead",
        "name": "save_lead",
        "description": "Persist the caller as a lead for this shop tenant. Call once per call after you have name + phone + intent.",
        "url": f"{BACKEND_URL}/api/shop-ai/save-lead",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Always pass {{tenant_id}} from dynamic_variables"},
                "retell_call_id": {"type": "string", "description": "Retell call_id"},
                "caller_name": {"type": "string"},
                "caller_phone": {"type": "string", "description": "10-digit phone, digits only"},
                "service_type": {"type": "string", "description": "e.g. 'oil change', 'brake inspection', 'DOT inspection'"},
                "vehicle": {"type": "string", "description": "Year/make/model or 'class 8 semi'"},
                "preferred_language": {"type": "string"},
                "intent": {
                    "type": "string",
                    "enum": ["new_lead", "appointment_request", "existing_customer", "quote_request", "other"],
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "emergency"],
                },
                "notes": {"type": "string"},
            },
            "required": ["tenant_id", "caller_name", "caller_phone", "intent"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-shopai-check-availability",
        "name": "check_availability",
        "description": (
            "Check whether the shop publishes live booking slots via Cal.com. "
            "If the response includes a 'slots' array with one or more entries, offer up to three "
            "to the caller verbatim from the 'human' field and remember the matching 'start' ISO so "
            "book_appointment can be called with slot_start_iso. If 'slots' is empty but booking_url "
            "is set, offer to text them the link via send_sms_followup. Otherwise take a message."
        ),
        "url": f"{BACKEND_URL}/api/shop-ai/check-availability",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "requested_window": {"type": "string", "description": "Caller phrase like 'tomorrow morning'"},
                "timezone": {"type": "string", "description": "IANA timezone of the caller if known"},
                "days_ahead": {"type": "integer", "description": "Look-ahead window, default 7"},
            },
            "required": ["tenant_id"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-shopai-book-appointment",
        "name": "book_appointment",
        "description": (
            "Book an appointment. If check_availability returned live Cal.com slots, pass the chosen "
            "slot's ISO string in slot_start_iso to create a real booking. Otherwise omit slot_start_iso "
            "and the team will follow up to confirm."
        ),
        "url": f"{BACKEND_URL}/api/shop-ai/book-appointment",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "retell_call_id": {"type": "string"},
                "caller_name": {"type": "string"},
                "caller_phone": {"type": "string"},
                "caller_email": {"type": "string", "description": "Caller email if provided"},
                "service_type": {"type": "string"},
                "vehicle": {"type": "string"},
                "slot_start_iso": {
                    "type": "string",
                    "description": "Exact ISO start time from check_availability.slots[*].start. Required for live booking.",
                },
                "requested_slot": {"type": "string", "description": "Free-form preferred time when no slot_start_iso"},
                "timezone": {"type": "string", "description": "IANA timezone, e.g. America/New_York"},
                "notes": {"type": "string"},
            },
            "required": ["tenant_id", "caller_name", "caller_phone"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-shopai-send-sms",
        "name": "send_sms_followup",
        "description": "Send the caller a short SMS follow-up (booking link, confirmation, address). Max one per call.",
        "url": f"{BACKEND_URL}/api/shop-ai/send-sms-followup",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "caller_phone": {"type": "string"},
                "body": {"type": "string", "description": "Plain-text SMS body, max 320 chars"},
                "retell_call_id": {"type": "string"},
            },
            "required": ["tenant_id", "caller_phone", "body"],
        },
    },
    {
        "type": "custom",
        "tool_id": "tool-shopai-save-summary",
        "name": "save_call_summary",
        "description": "Persist a one-paragraph summary of the call just before ending. Call exactly once at the end.",
        "url": f"{BACKEND_URL}/api/shop-ai/save-call-summary",
        "method": "POST",
        "headers": AUTH_HEADERS,
        "parameters": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "retell_call_id": {"type": "string"},
                "caller_phone": {"type": "string"},
                "summary": {"type": "string"},
                "intent": {"type": "string"},
                "urgency": {"type": "string"},
                "transcript": {"type": "string"},
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
                "Greet warmly: 'Thanks for calling {{shop_name}} — this is the AI receptionist. "
                "Who do I have the pleasure of speaking with?' Wait for their name, then ask: "
                "'And what's the best callback number for you?'"
            ),
        },
        "edges": [
            {
                "id": "edge-greet-to-intent",
                "destination_node_id": "intent-router",
                "transition_condition": {"type": "prompt", "prompt": "Caller has given a name and a callback phone number."},
            }
        ],
    },
    {
        "id": "intent-router",
        "type": "conversation",
        "display_position": {"x": 350, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": (
                "Ask: 'How can {{shop_name}} help you today — are you booking service, looking for a quote, "
                "checking on a vehicle that's already with us, or something else?' "
                "Classify the response into one of: appointment_request, quote_request, existing_customer, new_lead, other. "
                "If they mention fire/injury/crash, treat as emergency."
            ),
        },
        "edges": [
            {
                "id": "edge-to-emergency",
                "destination_node_id": "emergency-end",
                "transition_condition": {"type": "prompt", "prompt": "Caller described an emergency (fire, injury, crash, unsafe)."},
            },
            {
                "id": "edge-to-appointment",
                "destination_node_id": "appointment-collect",
                "transition_condition": {"type": "prompt", "prompt": "Caller wants to book an appointment or service slot."},
            },
            {
                "id": "edge-to-quote",
                "destination_node_id": "quote-collect",
                "transition_condition": {"type": "prompt", "prompt": "Caller wants a price quote or estimate."},
            },
            {
                "id": "edge-to-status",
                "destination_node_id": "status-collect",
                "transition_condition": {"type": "prompt", "prompt": "Caller is asking about a vehicle already at the shop."},
            },
            {
                "id": "edge-to-other",
                "destination_node_id": "lead-collect",
                "transition_condition": {"type": "prompt", "prompt": "Caller has a general question, wants to leave a message, or none of the above."},
            },
        ],
    },
    {
        "id": "appointment-collect",
        "type": "conversation",
        "display_position": {"x": 700, "y": -200},
        "instruction": {
            "type": "prompt",
            "text": (
                "Ask in one short turn: 'What type of service do you need, what kind of vehicle is it, "
                "and what day or time works best?' Capture service_type, vehicle, requested_slot."
            ),
        },
        "edges": [
            {
                "id": "edge-appt-to-check",
                "destination_node_id": "appointment-check-availability",
                "transition_condition": {"type": "prompt", "prompt": "Have service_type, vehicle, and requested_slot."},
            }
        ],
    },
    {
        "id": "appointment-check-availability",
        "type": "function",
        "display_position": {"x": 1050, "y": -200},
        "tool_id": "tool-shopai-check-availability",
        "tool_type": "custom",
        "name": "Call check_availability",
        "speak_during_execution": True,
        "wait_for_result": True,
        "instruction": {"type": "prompt", "text": "Call check_availability with tenant_id={{tenant_id}} and requested_window."},
        "edges": [
            {
                "id": "edge-check-to-book",
                "destination_node_id": "appointment-book",
                "transition_condition": {"type": "prompt", "prompt": "Tool returned a response."},
            }
        ],
    },
    {
        "id": "appointment-book",
        "type": "function",
        "display_position": {"x": 1400, "y": -200},
        "tool_id": "tool-shopai-book-appointment",
        "tool_type": "custom",
        "name": "Call book_appointment",
        "speak_during_execution": True,
        "wait_for_result": True,
        "instruction": {
            "type": "prompt",
            "text": (
                "Call book_appointment with tenant_id={{tenant_id}}, retell_call_id, caller_name, caller_phone, "
                "service_type, vehicle. If check_availability returned a 'slots' array and the caller picked one, "
                "pass slot_start_iso equal to that slot's 'start' value verbatim. Otherwise omit slot_start_iso and "
                "pass requested_slot as free text. If the response source is 'calcom_api', the appointment is confirmed."
            ),
        },
        "edges": [
            {
                "id": "edge-book-to-lead",
                "destination_node_id": "save-lead",
                "transition_condition": {"type": "prompt", "prompt": "Appointment booked or requested."},
            }
        ],
    },
    {
        "id": "quote-collect",
        "type": "conversation",
        "display_position": {"x": 700, "y": 0},
        "instruction": {
            "type": "prompt",
            "text": (
                "Ask for vehicle (year/make/model or class), the service they want quoted, and any "
                "specifics (parts already known, mileage). Tell them: 'I'll have the shop call or text you "
                "back with an estimate today.'"
            ),
        },
        "edges": [
            {
                "id": "edge-quote-to-lead",
                "destination_node_id": "save-lead",
                "transition_condition": {"type": "prompt", "prompt": "Have vehicle and service_type for the quote."},
            }
        ],
    },
    {
        "id": "status-collect",
        "type": "conversation",
        "display_position": {"x": 700, "y": 200},
        "instruction": {
            "type": "prompt",
            "text": (
                "Tell the caller: 'Let me get a message to the service writer — they'll call you right back "
                "with the latest on your vehicle.' Capture vehicle (year/make/model or unit number), and any "
                "callback preferences."
            ),
        },
        "edges": [
            {
                "id": "edge-status-to-lead",
                "destination_node_id": "save-lead",
                "transition_condition": {"type": "prompt", "prompt": "Captured vehicle and callback details."},
            }
        ],
    },
    {
        "id": "lead-collect",
        "type": "conversation",
        "display_position": {"x": 700, "y": 400},
        "instruction": {
            "type": "prompt",
            "text": (
                "Ask: 'What can I pass along to the team for you?' Capture a short notes string and "
                "ask if they'd like a callback or a text."
            ),
        },
        "edges": [
            {
                "id": "edge-other-to-lead",
                "destination_node_id": "save-lead",
                "transition_condition": {"type": "prompt", "prompt": "Have notes for the team."},
            }
        ],
    },
    {
        "id": "save-lead",
        "type": "function",
        "display_position": {"x": 1400, "y": 200},
        "tool_id": "tool-shopai-save-lead",
        "tool_type": "custom",
        "name": "Call save_lead",
        "speak_during_execution": False,
        "wait_for_result": True,
        "instruction": {
            "type": "prompt",
            "text": (
                "Call save_lead with tenant_id={{tenant_id}}, retell_call_id, caller_name, caller_phone, "
                "service_type, vehicle, intent, urgency, and notes."
            ),
        },
        "edges": [
            {
                "id": "edge-lead-to-confirm",
                "destination_node_id": "confirm-and-offer-sms",
                "transition_condition": {"type": "prompt", "prompt": "Lead saved."},
            }
        ],
    },
    {
        "id": "confirm-and-offer-sms",
        "type": "conversation",
        "display_position": {"x": 1750, "y": 200},
        "instruction": {
            "type": "prompt",
            "text": (
                "Confirm: 'Got it — I have your details on file at {{shop_name}}. The team will be in touch shortly.' "
                "If a booking_url was returned earlier OR the caller asked for a text, offer: "
                "'Want me to text you the details right now?' If yes, call send_sms_followup with a short, friendly body. "
                "Otherwise skip directly to the summary."
            ),
        },
        "edges": [
            {
                "id": "edge-confirm-to-sms",
                "destination_node_id": "send-sms",
                "transition_condition": {"type": "prompt", "prompt": "Caller agreed to a text follow-up."},
            },
            {
                "id": "edge-confirm-to-summary",
                "destination_node_id": "save-summary",
                "transition_condition": {"type": "prompt", "prompt": "Caller declined SMS or we are wrapping up."},
            },
        ],
    },
    {
        "id": "send-sms",
        "type": "function",
        "display_position": {"x": 2100, "y": 100},
        "tool_id": "tool-shopai-send-sms",
        "tool_type": "custom",
        "name": "Call send_sms_followup",
        "speak_during_execution": False,
        "wait_for_result": True,
        "instruction": {
            "type": "prompt",
            "text": "Call send_sms_followup with tenant_id={{tenant_id}}, caller_phone, retell_call_id, and a short friendly body.",
        },
        "edges": [
            {
                "id": "edge-sms-to-summary",
                "destination_node_id": "save-summary",
                "transition_condition": {"type": "prompt", "prompt": "SMS attempt complete."},
            }
        ],
    },
    {
        "id": "save-summary",
        "type": "function",
        "display_position": {"x": 2100, "y": 300},
        "tool_id": "tool-shopai-save-summary",
        "tool_type": "custom",
        "name": "Call save_call_summary",
        "speak_during_execution": False,
        "wait_for_result": True,
        "instruction": {
            "type": "prompt",
            "text": (
                "Call save_call_summary with tenant_id={{tenant_id}}, retell_call_id, caller_phone, "
                "a one-paragraph summary, the inferred intent, and the urgency."
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
        "display_position": {"x": 2450, "y": 300},
        "instruction": {
            "type": "prompt",
            "text": "Say warmly: 'Thanks for calling {{shop_name}}. Have a great day!' Then end the call.",
        },
        "edges": [],
    },
    {
        "id": "emergency-end",
        "type": "end",
        "display_position": {"x": 1050, "y": -400},
        "instruction": {
            "type": "prompt",
            "text": (
                "Say firmly and calmly: 'If anyone is hurt or in danger, please hang up and call 911 right now. "
                "Once you're safe, call {{shop_name}} back and we'll get a tow and a mechanic moving for you.' "
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
    print(f"Updating existing Shop Receptionist flow: {EXISTING_FLOW_ID}")
    flow_resp = retell("PATCH", f"/update-conversation-flow/{EXISTING_FLOW_ID}", FLOW)
    flow_id = flow_resp.get("conversation_flow_id", EXISTING_FLOW_ID)
    print(f"✅ Flow updated: {flow_id}")
else:
    print("Creating Shop Receptionist conversational flow...")
    flow_resp = retell("POST", "/create-conversation-flow", FLOW)
    flow_id = flow_resp["conversation_flow_id"]
    print(f"✅ Flow created: {flow_id}")

# ── Create or update agent ──────────────────────────────────────────────────
agent_body = {
    "agent_name": "Shop AI Receptionist — Roadcall",
    "response_engine": {"type": "conversation-flow", "conversation_flow_id": flow_id},
    "voice_id": "11labs-Lily",
    "language": "en-US",
    "interruption_sensitivity": 0.55,
    "responsiveness": 0.75,
    "voice_speed": 0.93,
    "voice_temperature": 0.75,
    "enable_backchannel": True,
    "backchannel_frequency": 0.4,
    "backchannel_words": ["okay", "got it", "mm-hmm", "sure"],
    "max_call_duration_ms": 1800000,
    "end_call_after_silence_ms": 60000,
    "boosted_keywords": [
        "oil change", "brake", "DOT inspection", "tire", "alignment",
        "appointment", "estimate", "quote", "tow", "engine light",
        "diesel", "transmission", "battery", "fleet",
    ],
    "normalize_for_speech": True,
}

if EXISTING_AGENT_ID:
    print(f"\nUpdating existing Shop Receptionist agent: {EXISTING_AGENT_ID}")
    agent_resp = retell("PATCH", f"/update-agent/{EXISTING_AGENT_ID}", agent_body)
    agent_id = agent_resp.get("agent_id", EXISTING_AGENT_ID)
    print(f"✅ Agent updated: {agent_id}")
else:
    print("\nCreating Shop Receptionist agent...")
    agent_resp = retell("POST", "/create-agent", agent_body)
    agent_id = agent_resp["agent_id"]
    print(f"✅ Agent created: {agent_id}")

print(f"\n{'='*60}")
print(f"  Shop Conversation Flow ID : {flow_id}")
print(f"  Shop Agent ID             : {agent_id}")
print(f"  Backend URL               : {BACKEND_URL}")
print(f"{'='*60}")
print("\nNext steps:")
print(f"  1. Set RETELL_SHOP_AGENT_ID={agent_id} in DO env (and locally in .env)")
print(f"  2. Set RETELL_SHOP_CONVERSATION_FLOW_ID={flow_id} in DO env")
print("  3. Per-tenant agents are spawned by the billing service activate_ai flow;")
print("     this script provisions the master flow + reference agent used as a template.")
print("  4. Verify RETELL_BACKEND_WEBHOOK_TOKEN matches the backend env var.")
