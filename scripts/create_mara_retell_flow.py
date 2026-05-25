#!/usr/bin/env python3
"""
Create the Roadcall.ai Mara front-desk agent in Retell.

Mara handles inbound calls to the company line (866) 623-3331.
She knows about Roadcall, answers basic questions, and warm-transfers
anything she can't handle to a live human at (727) 272-8156.

Reads RETELL_API_KEY from .env.

Safety:
  - Will NOT create a new agent unless ALLOW_NEW_MARA_AGENT=1
  - Will NOT reassign the phone number unless ASSIGN_MARA_NUMBER=1
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

RETELL_KEY = os.environ["RETELL_API_KEY"]
EXISTING_AGENT_ID = os.environ.get("MARA_AGENT_ID", "").strip()
EXISTING_FLOW_ID = os.environ.get("MARA_CONVERSATION_FLOW_ID", "").strip()

MARA_NUMBER = "+18666233331"
ESCALATION_NUMBER = "+17272728156"
SANDY_ROADSIDE_NUMBER = "(866) 818-3060"

if not EXISTING_AGENT_ID and os.environ.get("ALLOW_NEW_MARA_AGENT", "").strip().lower() not in {"1", "true", "yes"}:
    print("⚠️  MARA_AGENT_ID is not set — refusing to create a new Mara agent.")
    print("   To intentionally create Mara, re-run with ALLOW_NEW_MARA_AGENT=1.")
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
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print(f"HTTP {e.code} {method} {path}: {msg}")
        raise


GLOBAL_PROMPT = "\n".join([
    "You are Mara, the front desk voice for Roadcall.ai.",
    "Roadcall.ai is an AI-powered roadside dispatch platform that connects stranded drivers (passenger cars, pickups, fleet vehicles, semi-trucks and trailers) with vetted mobile mechanics and towing partners through a private nationwide directory.",
    "",
    "WHAT YOU KNOW ABOUT ROADCALL — answer briefly and confidently:",
    "• Who we are: Roadcall.ai is a private dispatch network with an AI dispatcher (Sandy) that takes the call, gathers the driver's location and problem, and matches the nearest qualified mechanic from our verified directory.",
    "• Who we serve: independent drivers, trucking companies, fleets, and repair shops that want either on-demand roadside help or steady dispatch leads.",
    "• Roadside emergency: if the caller is actually broken down right now, do NOT try to dispatch from this line. Politely give them the roadside number — " + SANDY_ROADSIDE_NUMBER + " — and tell them Sandy will pick up immediately and get them help.",
    "• For shops / mechanics: we add verified shops to the directory so they receive matched roadside jobs in their area.",
    "• For fleets: we provide a dispatch concierge that triages every breakdown call and routes to the right vendor.",
    "• Website: roadcall.ai",
    "",
    "STYLE: warm, calm, professional, short sentences. Sound like a real receptionist, not a chatbot. Don't read URLs letter-by-letter. Don't list bullet points out loud.",
    "",
    "HARD RULES:",
    "• Never invent pricing, contract terms, coverage areas, partner names, ETAs, or guarantees. If you don't know, say 'Let me get the right person on the line for that' and transfer.",
    "• If the caller is in danger, injured, or reports a fire or accident with injuries, tell them to hang up and call 911 immediately.",
    "• If the caller is broken down, redirect them to the roadside line " + SANDY_ROADSIDE_NUMBER + ".",
    "• For any sales question, partnership, billing, account change, complaint, press, or 'I want to speak to someone' — warm transfer to the live human line.",
    "",
    "TRANSFER BEHAVIOR: When you transfer, say one short line first such as 'One moment — connecting you to the team now.' Then trigger the transfer. Do not keep talking after the transfer line.",
])


FLOW = {
    "start_speaker": "agent",
    "model_choice": {"type": "cascading", "model": "gpt-4.1"},
    "model_temperature": 0.2,
    "tool_call_strict_mode": True,
    "global_prompt": GLOBAL_PROMPT,
    "tools": [],
    "nodes": [
        {
            "id": "start-node",
            "type": "conversation",
            "name": "Greeting",
            "display_position": {"x": 100, "y": 300},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Speak exactly once: 'Thanks for calling Roadcall. This is Mara — how can I help you today?' "
                    "Then stay silent and wait for the caller. Do not respond to silence or background noise. "
                    "Once the caller speaks, identify what they need:\n"
                    " • Roadside emergency / broken down right now → route to 'roadside-redirect'.\n"
                    " • Sales, partnership, pricing, billing, account, complaint, press, or 'speak to a person' → route to 'transfer-human'.\n"
                    " • General question you can answer briefly from what you know about Roadcall → answer in one or two sentences, then ask if there is anything else. If they want more detail or want a person, route to 'transfer-human'."
                )
            },
            "edges": [
                {
                    "id": "edge-start-roadside",
                    "destination_node_id": "roadside-redirect",
                    "transition_condition": {
                        "type": "prompt",
                        "prompt": "Caller is broken down, stranded, needs a tow, has a flat, dead battery, mechanical issue, or is otherwise asking for roadside help right now."
                    }
                },
                {
                    "id": "edge-start-transfer",
                    "destination_node_id": "transfer-human",
                    "transition_condition": {
                        "type": "prompt",
                        "prompt": "Caller asked for sales, partnership, pricing, billing, account help, complaint, press, or wants to speak to a person."
                    }
                }
            ]
        },
        {
            "id": "roadside-redirect",
            "type": "conversation",
            "name": "Roadside Redirect",
            "display_position": {"x": 500, "y": 100},
            "instruction": {
                "type": "prompt",
                "text": (
                    "Speak warmly and briefly: 'I'm so sorry you're stuck. This line is our main office — please hang up and call our roadside line at " + SANDY_ROADSIDE_NUMBER + ". Sandy will answer right away and get you help. Do you have a pen, or want me to repeat the number?' "
                    "If they ask you to repeat, repeat the number slowly once. Then end the call politely."
                )
            },
            "edges": []
        },
        {
            "id": "transfer-human",
            "type": "transfer_call",
            "name": "Warm Transfer to Live Human",
            "display_position": {"x": 500, "y": 500},
            "instruction": {
                "type": "static_text",
                "text": "One moment — connecting you to the team now."
            },
            "transfer_destination": {
                "type": "predefined",
                "number": ESCALATION_NUMBER
            },
            "transfer_option": {
                "type": "cold_transfer"
            }
        }
    ]
}


# ── Create / update flow ─────────────────────────────────
if EXISTING_FLOW_ID:
    print(f"Updating existing Mara flow: {EXISTING_FLOW_ID}")
    flow_resp = retell("PATCH", f"/update-conversation-flow/{EXISTING_FLOW_ID}", FLOW)
    flow_id = flow_resp.get("conversation_flow_id", EXISTING_FLOW_ID)
    print(f"✅ Conversation flow updated: {flow_id}")
else:
    print("Creating Mara conversational flow...")
    flow_resp = retell("POST", "/create-conversation-flow", FLOW)
    flow_id = flow_resp["conversation_flow_id"]
    print(f"✅ Conversation flow created: {flow_id}")


# ── Create / update agent ────────────────────────────────
agent_body = {
    "agent_name": "Mara — Roadcall.ai Front Desk",
    "response_engine": {"type": "conversation-flow", "conversation_flow_id": flow_id},
    "voice_id": "11labs-Cimo",  # warm professional female; will fall back if unavailable
    "language": "en-US",
    "interruption_sensitivity": 0.3,
    "responsiveness": 0.7,
    "voice_speed": 0.97,
    "voice_temperature": 0.7,
    "begin_message_delay_ms": 500,
    "denoising_mode": "noise-and-background-speech-cancellation",
    "enable_backchannel": True,
    "backchannel_frequency": 0.4,
    "backchannel_words": ["okay", "of course", "right", "mm-hm"],
    "max_call_duration_ms": 900000,
    "end_call_after_silence_ms": 60000,
    "boosted_keywords": ["Roadcall", "Mara", "Sandy", "dispatcher", "mechanic", "fleet", "trucking", "partnership"],
    "normalize_for_speech": True,
}

if EXISTING_AGENT_ID:
    print(f"\nUpdating existing Mara agent: {EXISTING_AGENT_ID}")
    try:
        agent_resp = retell("PATCH", f"/update-agent/{EXISTING_AGENT_ID}", agent_body)
    except urllib.error.HTTPError:
        # voice may not exist on this account; retry with safe default
        agent_body["voice_id"] = "11labs-Lily"
        agent_resp = retell("PATCH", f"/update-agent/{EXISTING_AGENT_ID}", agent_body)
    agent_id = agent_resp.get("agent_id", EXISTING_AGENT_ID)
    print(f"✅ Agent updated: {agent_id}")
else:
    print("\nCreating Mara agent...")
    try:
        agent_resp = retell("POST", "/create-agent", agent_body)
    except urllib.error.HTTPError:
        agent_body["voice_id"] = "11labs-Lily"
        agent_resp = retell("POST", "/create-agent", agent_body)
    agent_id = agent_resp["agent_id"]
    print(f"✅ Agent created: {agent_id}")


# ── Optionally assign phone number ───────────────────────
assign = os.environ.get("ASSIGN_MARA_NUMBER", "").strip().lower() in {"1", "true", "yes"}
if assign:
    print(f"\nAssigning {MARA_NUMBER} to Mara ({agent_id})...")
    try:
        retell("PATCH", f"/update-phone-number/{MARA_NUMBER}", {
            "inbound_agent_id": agent_id,
            "outbound_agent_id": agent_id,
        })
        print(f"✅ {MARA_NUMBER} now routes to Mara.")
    except urllib.error.HTTPError as e:
        print(f"⚠️  Phone assignment failed: {e}. Assign manually in the Retell dashboard.")
else:
    print(f"\nℹ️  Skipped phone assignment. Re-run with ASSIGN_MARA_NUMBER=1 to attach {MARA_NUMBER}.")

print(f"\n{'='*60}")
print(f"  Conversation Flow ID : {flow_id}")
print(f"  Agent ID             : {agent_id}")
print(f"  Agent Name           : Mara — Roadcall.ai Front Desk")
print(f"  Phone (target)       : {MARA_NUMBER}")
print(f"  Escalation target    : {ESCALATION_NUMBER}")
print(f"{'='*60}")
