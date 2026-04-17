"""LiveKit AI Agent Worker for Roadside Assistance.

LiveKit Cloud handles LLM, TTS, STT, SIP trunking.
This agent connects to LiveKit Cloud and handles three call types:

1. INBOUND (driver_intake):
   Driver calls in → agent collects info → creates job via backend API
   → sends magic-link SMS → done.

2. OUTBOUND (mechanic_dispatch):
   Backend dials a mechanic → agent pitches the job → records response
   via backend API.

3. INBOUND (shop_inbound):
   Customer calls a shop's AI number → agent acts as the shop's
   receptionist using their custom config.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)

load_dotenv()

logger = logging.getLogger("roadcall-agent")
logger.setLevel(logging.INFO)

# Seconds to wait for the SIP leg before prompting the agent (outbound / inbound)
_SIP_PARTICIPANT_TIMEOUT_S = float(os.getenv("SIP_PARTICIPANT_TIMEOUT_S", "60"))

# LiveKit Inference model IDs (STT → LLM → TTS). Without these, AgentSession has no
# llm/stt/tts and generate_reply() raises — the agent will never speak.
# See: https://docs.livekit.io/agents/models/
# NOTE: The "Agents" UI in LiveKit Cloud (e.g. Blake) is a separate hosted product;
# this self-hosted worker must still declare inference models here.
_DEFAULT_INFERENCE_LLM = "openai/gpt-4o-mini"
_DEFAULT_INFERENCE_STT = "deepgram/nova-2-phonecall"
_DEFAULT_INFERENCE_TTS = "cartesia/sonic-3"

# Backend API base URL for database operations
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


# ─── Shared HTTP helper ────────────────────────────────


async def api_call(
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
) -> dict:
    """Make an authenticated call to the backend API."""
    url = f"{BACKEND_URL}/api{path}"
    headers = {"X-Admin-Key": ADMIN_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.request(
            method, url, json=json_body, params=params, headers=headers
        )
        resp.raise_for_status()
        return resp.json()


# ─── Dataclass for per-call state ───────────────────────


@dataclass
class CallState:
    """Mutable state bag attached to AgentSession.userdata."""

    room_metadata: dict = field(default_factory=dict)
    collected: dict = field(default_factory=dict)
    ctx: Any = None  # JobContext reference


async def _wait_for_sip_participant(
    ctx: JobContext,
    *,
    identity: str | None,
    timeout_s: float = _SIP_PARTICIPANT_TIMEOUT_S,
) -> None:
    """Block until the phone leg is in the room so the first utterance is not lost."""
    try:
        await asyncio.wait_for(
            ctx.wait_for_participant(
                identity=identity,
                kind=rtc.ParticipantKind.PARTICIPANT_KIND_SIP,
            ),
            timeout=timeout_s,
        )
        logger.info("SIP participant ready (identity=%s)", identity or "any")
    except asyncio.TimeoutError:
        logger.warning(
            "Timeout waiting for SIP participant (identity=%s) — continuing anyway",
            identity or "any",
        )
    except Exception as e:
        logger.warning("wait_for_participant failed: %s", e)


def _inference_tts_model_string() -> str:
    tts = os.getenv("LIVEKIT_INFERENCE_TTS", _DEFAULT_INFERENCE_TTS)
    voice = os.getenv("LIVEKIT_INFERENCE_TTS_VOICE", "").strip()
    if voice and ":" not in tts:
        return f"{tts}:{voice}"
    return tts


def _voice_agent_session(
    *,
    userdata: Any,
    min_endpointing_delay: float,
    max_endpointing_delay: float,
) -> AgentSession:
    """Wire LiveKit Cloud Inference (billing is via your LiveKit project)."""
    llm_id = os.getenv("LIVEKIT_INFERENCE_LLM", _DEFAULT_INFERENCE_LLM)
    stt_id = os.getenv("LIVEKIT_INFERENCE_STT", _DEFAULT_INFERENCE_STT)
    tts_id = _inference_tts_model_string()
    logger.info(
        "Voice pipeline: llm=%s stt=%s tts=%s",
        llm_id,
        stt_id,
        tts_id.split(":", 1)[0],
    )
    return AgentSession(
        llm=llm_id,
        stt=stt_id,
        tts=tts_id,
        turn_handling={
            "turn_detection": "stt",
            "endpointing": {
                "min_delay": min_endpointing_delay,
                "max_delay": max_endpointing_delay,
            },
            "interruption": {"enabled": True},
        },
        userdata=userdata,
    )


def _kickoff_agent_speech(session: AgentSession, instructions: str) -> None:
    """Start a model turn without waiting for user speech (required for telephony)."""
    try:
        session.generate_reply(instructions=instructions)
    except RuntimeError as e:
        logger.error(
            "Could not start agent speech (%s). "
            "Ensure LIVEKIT_INFERENCE_LLM/STT/TTS are set on the worker.",
            e,
        )


# ════════════════════════════════════════════════════════
#  SYSTEM PROMPTS
# ════════════════════════════════════════════════════════


DRIVER_INTAKE_PROMPT = """\
You're Sam from Roadside Assist — a calm, friendly human dispatcher who picks up \
when someone's stuck on the side of the road.

**Personality rules (never break these):**
- Talk like a real person: use contractions, "yeah", "gotcha", "alright", brief \
filler like "okay" or "sure thing".
- NEVER say "I am an AI" or "as an AI assistant".  You are Sam.
- Mirror the caller's energy — if they're panicked, be soothing first, THEN \
collect info.  If they're chill, keep it light.
- Use short sentences.  One thought per sentence.  Pause naturally.
- Don't repeat the caller's answers back robotically.  Weave confirmations in \
casually: "Got it — a 2019 Camry, flat tire on the highway."
- Never list numbered steps out loud ("Step one … step two …").

**What you need to collect (in any natural order):**
1. Their first name.
2. Vehicle — make/model, year if they mention it.
3. What happened — flat tire, dead battery, locked out, need a tow, etc.
4. Their current location — city and state, or the nearest town if they don't know the exact city.
5. One-line situation note (e.g. "shoulder of I-95 southbound near exit 12").

**Once you have everything:**
- Confirm it back in ONE casual sentence.
- Call `find_nearby_mechanics` with the caller's city, state, and issue type.
- Briefly tell them the best 2–3 mechanics you found in their area.
- Call the `save_driver_info` tool.
- Then wrap up warmly: "I've got your info down and I'm lining up help in your area. Stay safe out there."

Keep the whole call under 90 seconds.  No corporate jargon.\
"""

MECHANIC_DISPATCH_PROMPT = """\
You're calling from Roadside Assist dispatch.  You're a friendly, no-nonsense \
dispatcher checking if a mechanic can take a job.

**Personality rules:**
- Sound like a human dispatcher on a busy shift — polite but efficient.
- Use the mechanic's name.  Be warm but brief.
- Don't read a script.  Summarize the job in plain language.

**Job details:**
{job_summary}

**Call flow:**
1. "Hey {mechanic_name}, this is dispatch at Roadside Assist — got a quick one \
for you."
2. Briefly describe the job (what happened, vehicle type, rough area).
3. Ask if they can take it and how long to get there.
4. If yes → call `record_mechanic_response` with "accepted" and their ETA.
5. If no → say "No worries, appreciate you" and call `record_mechanic_response` \
with "declined".
6. If voicemail → call `record_mechanic_response` with "no_answer" and hang up.

Keep it under 45 seconds.\
"""


# ════════════════════════════════════════════════════════
#  TOOLS — Driver Intake
# ════════════════════════════════════════════════════════


@llm.function_tool(
    description=(
        "Save the driver's collected information and create a job in the system. "
        "Call this once you have the driver's name, vehicle, issue type, and a "
        "brief situation note, plus their current city and state."
    )
)
async def save_driver_info(
    driver_name: str,
    vehicle_type: str,
    issue_type: str,
    driver_city: str,
    driver_state: str,
    situation_note: str,
):
    """Persist intake data so dispatch can continue after the call."""
    normalized_issue = _normalize_issue_type(issue_type)

    # Retrieve the caller's phone number stored in CallState by the entrypoint
    driver_phone = _current_caller_phone or ""

    try:
        result = await api_call(
            "POST",
            "/jobs",
            json_body={
                "driver_name": driver_name,
                "driver_phone": driver_phone,
                "vehicle_type": vehicle_type,
                "driver_city": driver_city,
                "driver_state": driver_state,
                "issue_type": normalized_issue,
                "issue_summary": situation_note,
            },
        )
        job_id = result.get("public_job_id", "unknown")
        logger.info(f"Job created via API: {job_id} for {driver_name} ({driver_phone})")
        return (
            f"Done — job {job_id} is in the system for {driver_name}. "
            f"Let them know you're lining up help in {driver_city}, {driver_state}."
        )
    except Exception as e:
        logger.error(f"Failed to create job via API: {e}")
        return (
            f"Information saved. Let {driver_name} know you're checking the "
            f"best options near {driver_city}, {driver_state}."
        )


# Module-level variables set per-call by handlers (tools read these)
_current_caller_phone: str = ""
_current_dispatch_job_id: str = ""
_current_dispatch_attempt_id: str = ""


# ════════════════════════════════════════════════════════
#  TOOLS — Mechanic Dispatch
# ════════════════════════════════════════════════════════


@llm.function_tool(
    description=(
        "Record the mechanic's response to the dispatch request. "
        "You MUST call this before the call ends."
    )
)
async def record_mechanic_response(
    response: str,
    eta_minutes: int = 0,
    notes: str = "",
):
    """Save whether the mechanic accepted/declined, with optional ETA."""
    global _current_dispatch_job_id, _current_dispatch_attempt_id

    normalized = _normalize_mechanic_response(response)
    logger.info(f"Mechanic response: {normalized}, ETA: {eta_minutes}min")

    if not _current_dispatch_job_id or not _current_dispatch_attempt_id:
        logger.error("record_mechanic_response: missing job/dispatch context")
        return "Couldn't log the response — system error. Hang up."

    try:
        await api_call(
            "POST",
            f"/dispatch/{_current_dispatch_job_id}/mechanic-response",
            json_body={
                "dispatch_attempt_id": _current_dispatch_attempt_id,
                "response": normalized,
                "eta_minutes": eta_minutes if eta_minutes > 0 else None,
                "notes": notes or None,
            },
        )
    except Exception as e:
        logger.error(f"Failed to record mechanic response via API: {e}")
        return "Having trouble saving that — try again briefly."

    if normalized == "accepted":
        return f"Confirmed — logged acceptance with a {eta_minutes}-minute ETA."
    if normalized == "no_answer":
        return "Noted — no answer. Moving to the next mechanic."
    return "Got it — they can't take this one."


@llm.function_tool(
    description=(
        "Look up nearby mechanics from the database for a given location. "
        "Use this to find available mechanics near the driver."
    )
)
async def find_nearby_mechanics(
    latitude: float | None = None,
    longitude: float | None = None,
    city: str = "",
    state: str = "",
    issue_type: str = "",
    limit: int = 5,
):
    """Query the backend for the closest available mechanics."""
    try:
        params: dict[str, Any] = {"limit": limit}
        if latitude is not None and longitude is not None:
            params["lat"] = latitude
            params["lng"] = longitude
        elif city and state:
            params["city"] = city
            params["state"] = state
        else:
            return "I need either GPS coordinates or a city and state to look up mechanics."

        if issue_type:
            params["issue_type"] = issue_type

        result = await api_call("GET", "/mechanics", params=params)
        mechanics = result if isinstance(result, list) else result.get("items", [])

        if not mechanics:
            return "No available mechanics found near that location right now."

        lines = []
        for m in mechanics[:limit]:
            name = m.get("company_name", "Unknown")
            phone = m.get("phone", "")
            dist = m.get("distance_miles")
            rating = m.get("rating", "N/A")
            area = ", ".join(filter(None, [m.get("city"), m.get("state")])) or "area unknown"
            distance_text = f"{dist} mi away" if dist is not None else area
            lines.append(f"- {name} ({phone}) — {distance_text}, rated {rating}")

        return "Closest mechanics:\n" + "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to look up mechanics: {e}")
        return "Couldn't look up nearby mechanics right now."


@llm.function_tool(
    description="Check the current status of an existing job by its public ID."
)
async def check_job_status(job_id: str):
    """Look up a job's current state from the database."""
    try:
        result = await api_call("GET", f"/jobs/{job_id}")
        status = result.get("status", "unknown")
        driver = result.get("driver_name", "")
        vehicle = result.get("vehicle_type", "")
        issue = result.get("issue_type", "")
        return (
            f"Job {job_id}: {status}. "
            f"Driver: {driver}, Vehicle: {vehicle}, Issue: {issue}."
        )
    except Exception as e:
        logger.error(f"Failed to check job status: {e}")
        return f"Couldn't look up job {job_id} right now."


# ════════════════════════════════════════════════════════
#  TOOLS — Shop Inbound
# ════════════════════════════════════════════════════════


@llm.function_tool(
    description=(
        "Save the caller's information from a shop inbound call. "
        "Call this once you have their name, what they need, and vehicle info."
    )
)
async def save_call_info(
    caller_name: str,
    vehicle_info: str = "",
    service_needed: str = "",
    urgency: str = "normal",
    notes: str = "",
):
    """Persist caller data for the shop to follow up on."""
    logger.info(f"Shop call data: {caller_name}, service={service_needed}")
    return (
        f"All noted, {caller_name}. Someone from the shop will follow up with "
        f"you shortly. Anything else I can help with?"
    )


@llm.function_tool(
    description=(
        "Transfer the call to a human at the shop. "
        "Use this only if the caller specifically asks to speak to a person."
    )
)
async def transfer_to_human(reason: str = "Caller requested"):
    """Flag the call for human transfer."""
    logger.info(f"Transfer requested: {reason}")
    return "Transferring you now — one moment please."


# ════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════


async def entrypoint(ctx: JobContext):
    """Main entry — LiveKit calls this when a room needs an agent."""
    await ctx.connect()

    room_metadata_raw = ctx.room.metadata or "{}"
    try:
        room_metadata = json.loads(room_metadata_raw)
    except (json.JSONDecodeError, TypeError):
        room_metadata = {}

    call_type = room_metadata.get("type", "")
    # Inbound SIP often omits room metadata — treat as driver intake
    if not call_type:
        room_metadata = {**room_metadata, "type": "driver_intake"}
        call_type = "driver_intake"

    if call_type == "driver_intake":
        await handle_driver_intake(ctx, room_metadata)
    elif call_type == "mechanic_dispatch":
        await handle_mechanic_dispatch(ctx, room_metadata)
    elif call_type == "shop_inbound":
        await handle_shop_inbound(ctx, room_metadata)
    else:
        logger.warning(f"Unknown room type: {call_type}, room: {ctx.room.name}")


# ─── Driver Intake ──────────────────────────────────────


async def handle_driver_intake(ctx: JobContext, meta: dict):
    logger.info(f"Driver intake call in room {ctx.room.name}")

    # Extract the caller's phone number from SIP participant info
    global _current_caller_phone
    _current_caller_phone = ""
    for p in ctx.room.remote_participants.values():
        # SIP participants have the caller's number in their identity or attributes
        identity = p.identity or ""
        attrs = p.attributes or {}
        phone = (
            attrs.get("sip.phoneNumber")
            or attrs.get("sip.from")
            or attrs.get("sip.callId")
            or ""
        )
        if not phone and identity.startswith("sip_"):
            phone = identity.replace("sip_", "+")
        if phone:
            # Clean SIP URI format: sip:+15551234567@trunk → +15551234567
            if phone.startswith("sip:"):
                phone = phone.split("@")[0].replace("sip:", "")
            _current_caller_phone = phone
            logger.info(f"Extracted caller phone: {phone}")
            break

    # Also check room metadata for caller_phone (set by SIP trunk config)
    if not _current_caller_phone:
        _current_caller_phone = meta.get("caller_phone", "")

    state = CallState(
        room_metadata=meta,
        ctx=ctx,
        collected={"caller_phone": _current_caller_phone},
    )

    agent = Agent(
        instructions=DRIVER_INTAKE_PROMPT,
        tools=[find_nearby_mechanics, save_driver_info],
    )

    session = _voice_agent_session(
        userdata=state,
        min_endpointing_delay=0.5,
        max_endpointing_delay=5.0,
    )

    await session.start(agent=agent, room=ctx.room)
    await _wait_for_sip_participant(ctx, identity=None)
    _kickoff_agent_speech(
        session,
        instructions=(
            "A driver is on the line (roadside assistance). "
            "Immediately greet them as Sam from Roadside Assist and start helping — "
            "do not wait in silence for them to speak first."
        ),
    )
    logger.info(f"Driver intake agent running in {ctx.room.name} (caller: {_current_caller_phone})")


# ─── Mechanic Dispatch ─────────────────────────────────


async def handle_mechanic_dispatch(ctx: JobContext, meta: dict):
    global _current_dispatch_job_id, _current_dispatch_attempt_id

    mechanic_name = meta.get("mechanic_name", "there")
    job_summary = meta.get("job_summary", "a roadside job nearby")
    job_id = meta.get("job_id", "")
    dispatch_attempt_id = meta.get("dispatch_attempt_id", "")
    _current_dispatch_job_id = job_id
    _current_dispatch_attempt_id = dispatch_attempt_id

    logger.info(
        f"Dispatch call in {ctx.room.name} to {mechanic_name} for job {job_id}"
    )

    prompt = MECHANIC_DISPATCH_PROMPT.format(
        job_summary=job_summary, mechanic_name=mechanic_name
    )

    state = CallState(
        room_metadata=meta,
        ctx=ctx,
        collected={
            "job_id": job_id,
            "dispatch_attempt_id": dispatch_attempt_id,
            "mechanic_name": mechanic_name,
        },
    )

    agent = Agent(
        instructions=prompt,
        tools=[record_mechanic_response],
    )

    session = _voice_agent_session(
        userdata=state,
        min_endpointing_delay=0.4,
        max_endpointing_delay=3.0,
    )

    await session.start(agent=agent, room=ctx.room)
    await _wait_for_sip_participant(
        ctx,
        identity=f"mechanic-{dispatch_attempt_id}",
    )
    _kickoff_agent_speech(
        session,
        instructions=(
            "The mechanic just answered your outbound call. "
            "Speak immediately: greet them by name, summarize the roadside job briefly, "
            "and ask if they can take it — do not wait for them to talk first."
        ),
    )
    logger.info(f"Dispatch agent running in {ctx.room.name}")


# ─── Shop Inbound ──────────────────────────────────────


async def handle_shop_inbound(ctx: JobContext, meta: dict):
    shop_id = meta.get("shop_id", "")
    business_name = meta.get("business_name", "the shop")
    caller_phone = meta.get("caller_phone", "unknown")
    custom_prompt = meta.get("prompt", "")
    greeting = meta.get("greeting", "")

    logger.info(
        f"Shop inbound in {ctx.room.name} for {business_name} from {caller_phone}"
    )

    prompt = custom_prompt or (
        f"You're the friendly AI receptionist for {business_name}. "
        f"Answer calls naturally — no robotic scripts. Help callers with "
        f"service questions, scheduling, pricing ballparks, and general info. "
        f"If they want to book, collect their name, phone, vehicle info, and "
        f"what they need done, then call save_call_info. "
        f"If they insist on speaking to a human, call transfer_to_human."
    )

    state = CallState(
        room_metadata=meta,
        ctx=ctx,
        collected={"shop_id": shop_id, "caller_phone": caller_phone},
    )

    agent = Agent(
        instructions=prompt,
        tools=[save_call_info, transfer_to_human],
    )

    session = _voice_agent_session(
        userdata=state,
        min_endpointing_delay=0.5,
        max_endpointing_delay=5.0,
    )

    await session.start(agent=agent, room=ctx.room)
    await _wait_for_sip_participant(ctx, identity=None)

    # Say the custom greeting immediately if configured
    if greeting:
        await session.say(greeting)
    else:
        _kickoff_agent_speech(
            session,
            instructions=(
                f"A caller just reached {business_name}. "
                "Greet them professionally and help with their request — speak first."
            ),
        )

    logger.info(f"Shop agent running for {business_name} in {ctx.room.name}")


# ════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════


def _normalize_mechanic_response(raw: str) -> str:
    lower = raw.lower().strip()
    if lower in ("accepted", "declined", "unavailable", "no_answer"):
        return lower
    if any(w in lower for w in ("yes", "accept", "available", "sure", "on my way")):
        return "accepted"
    if any(w in lower for w in ("no", "decline", "can't", "cannot", "busy")):
        return "declined"
    if any(w in lower for w in ("voicemail", "no answer", "didn't pick")):
        return "no_answer"
    return "unavailable"


def _normalize_issue_type(raw: str) -> str:
    raw_lower = raw.lower()
    mappings = {
        "flat_tire": ["flat tire", "tire", "puncture", "blowout", "flat"],
        "dead_battery": ["battery", "dead battery", "won't start", "jump start", "jump"],
        "lockout": ["locked out", "lockout", "keys locked", "locked keys", "lock"],
        "fuel_delivery": ["fuel", "gas", "ran out of gas", "out of fuel", "no gas"],
        "tow_needed": ["tow", "towing", "need a tow", "can't drive", "won't move"],
        "engine_trouble": ["engine", "stalled", "engine trouble", "misfire"],
        "overheating": ["overheat", "overheating", "coolant", "radiator", "steam"],
        "accident": ["accident", "crash", "collision", "hit"],
        "stuck_off_road": ["stuck", "off road", "ditch", "mud", "snow"],
    }
    for enum_val, keywords in mappings.items():
        if any(kw in raw_lower for kw in keywords):
            return enum_val
    return "other"


# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=os.getenv("LIVEKIT_AGENT_NAME", "roadcall-agent"),
            api_key=os.getenv("LIVEKIT_API_KEY", ""),
            api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
            ws_url=os.getenv("LIVEKIT_URL", ""),
        )
    )