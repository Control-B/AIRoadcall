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
from livekit.plugins import deepgram, elevenlabs
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
_SIP_PARTICIPANT_TIMEOUT_S = float(os.getenv("SIP_PARTICIPANT_TIMEOUT_S", "10"))
# Brief guard after SIP join before first TTS playback so telephony audio is attached.
_FIRST_SPEECH_SETTLE_DELAY_S = float(os.getenv("FIRST_SPEECH_SETTLE_DELAY_S", "1.0"))

# LiveKit Inference model IDs (STT → LLM → TTS). Without these, AgentSession has no
# llm/stt/tts and generate_reply() raises — the agent will never speak.
# See: https://docs.livekit.io/agents/models/
# NOTE: The "Agents" UI in LiveKit Cloud (e.g. Blake) does not drive this process.
# SIP/telephony jobs are handled by THIS worker's prompts below unless you route
# calls to a hosted agent instead. Set AGENT_DRIVER_INTAKE_PROMPT to mirror console text.
_DEFAULT_INFERENCE_LLM = "openai/gpt-4o-mini"
# ElevenLabs multilingual v2 — direct plugin, supports 29+ languages
_DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"
_SARAH_VOICE_ID = "nf4MCGNSdM0hxM95ZBQR"
_DEFAULT_ELEVENLABS_VOICE_ID = _SARAH_VOICE_ID  # Sarah voice
# Speaking rate: 0.85 = ~15% slower than default (1.0). Range: 0.7–1.2
_DEFAULT_SPEAKING_RATE = float(os.getenv("AGENT_SPEAKING_RATE", "0.85"))

# Backend API base URL for database operations
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


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
    headers = {"Content-Type": "application/json"}
    if ADMIN_API_KEY.strip():
        headers["X-Admin-Key"] = ADMIN_API_KEY.strip()
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.request(
                method, url, json=json_body, params=params, headers=headers
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Backend API HTTP error %s %s -> %s body=%s",
                method,
                url,
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise
        except Exception as exc:
            logger.error("Backend API request failed %s %s: %s", method, url, exc)
            raise


async def load_caller_memory(phone: str) -> str:
    """Fetch recent summaries and pronunciation hints for a returning caller."""
    normalized = phone.strip()
    if not normalized:
        return ""

    try:
        result = await api_call("GET", "/call-summaries/memory", params={"phone": normalized, "limit": 3})
    except Exception as exc:
        logger.warning("Failed to load caller memory for %s: %s", normalized, exc)
        return ""

    summaries = result.get("recent_summaries", [])
    pronunciation_hints = result.get("pronunciation_hints", [])
    memory_notes = result.get("memory_notes", [])

    sections: list[str] = []
    if pronunciation_hints:
        sections.append(
            "Pronunciation hints for this caller or related contacts: "
            + "; ".join(str(item) for item in pronunciation_hints[:5])
        )
    if memory_notes:
        sections.append(
            "Persistent memory notes: " + " ; ".join(str(item) for item in memory_notes[:5])
        )
    if summaries:
        summary_lines = []
        for item in summaries[:3]:
            text = str(item.get("summary_text") or "").strip()
            if text:
                summary_lines.append(f"- {text}")
        if summary_lines:
            sections.append("Recent conversations:\n" + "\n".join(summary_lines))

    if not sections:
        return ""
    return "\n\n".join(sections)


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
        logger.error(
            "Timeout waiting for SIP participant (identity=%s) — disconnecting room",
            identity or "any",
        )
        await ctx.room.disconnect()
        raise
    except Exception as e:
        logger.warning("wait_for_participant failed: %s", e)


def _voice_agent_session(
    *,
    userdata: Any,
    min_endpointing_delay: float,
    max_endpointing_delay: float,
) -> AgentSession:
    """Voice pipeline: ElevenLabs TTS (direct) + LiveKit Inference STT."""
    llm_id = os.getenv("LIVEKIT_INFERENCE_LLM", _DEFAULT_INFERENCE_LLM)
    configured_tts = os.getenv("LIVEKIT_INFERENCE_TTS", "").strip()
    if configured_tts.startswith("elevenlabs/"):
        el_model = configured_tts.split("/", 1)[1] or _DEFAULT_ELEVENLABS_MODEL
    else:
        el_model = os.getenv("ELEVENLABS_MODEL", _DEFAULT_ELEVENLABS_MODEL)

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "").strip() or _DEFAULT_ELEVENLABS_VOICE_ID
    legacy_voice_id = os.getenv("LIVEKIT_INFERENCE_TTS_VOICE", "").strip()
    if legacy_voice_id and legacy_voice_id != voice_id:
        logger.warning(
            "Ignoring LIVEKIT_INFERENCE_TTS_VOICE=%s in favor of ELEVENLABS_VOICE_ID=%s",
            legacy_voice_id,
            voice_id,
        )
    stt_id = os.getenv("LIVEKIT_INFERENCE_STT", "deepgram/nova-2-phonecall")
    elevenlabs_api_key = (
        os.getenv("ELEVENLABS_API_KEY", "").strip()
        or os.getenv("ELEVEN_API_KEY", "").strip()
        or None
    )

    if not elevenlabs_api_key:
        logger.error(
            "ElevenLabs API key is missing. Set ELEVENLABS_API_KEY on the worker "
            "when LIVEKIT_INFERENCE_TTS uses an elevenlabs/* voice."
        )

    logger.info(
        "Voice pipeline: llm=%s tts=elevenlabs/%s voice=%s stt=%s",
        llm_id, el_model, voice_id, stt_id,
    )
    return AgentSession(
        llm=llm_id,
        tts=elevenlabs.TTS(
            model=el_model,
            voice_id=voice_id,
            api_key=elevenlabs_api_key,
        ),
        stt=stt_id,
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


async def _kickoff_agent_speech(
    session: AgentSession,
    instructions: str,
    *,
    initial_delay_s: float = 0.0,
) -> None:
    """Start a model turn without waiting for user speech (required for telephony)."""
    try:
        if initial_delay_s > 0:
            await asyncio.sleep(initial_delay_s)
        handle = session.generate_reply(instructions=instructions)
        await handle.wait_for_playout()
    except RuntimeError as e:
        logger.error(
            "Could not start agent speech (%s). "
            "Ensure LIVEKIT_INFERENCE_LLM/STT/TTS are set on the worker.",
            e,
        )
    except Exception as e:
        logger.exception("Agent speech failed: %s", e)


async def _speak_text_with_retry(
    session: AgentSession,
    text: str,
    *,
    label: str,
    attempts: int = 2,
    initial_delay_s: float = 0.0,
) -> bool:
    """Speak literal text with a short retry window for telephony race conditions."""
    spoken_text = (text or "").strip()
    if not spoken_text:
        return False

    for attempt in range(1, attempts + 1):
        try:
            logger.info("%s attempt %s starting", label, attempt)
            if attempt == 1 and initial_delay_s > 0:
                await asyncio.sleep(initial_delay_s)
            elif attempt > 1:
                await asyncio.sleep(0.4)

            handle = session.say(
                spoken_text,
                allow_interruptions=False,
                add_to_chat_ctx=True,
            )
            await handle.wait_for_playout()
            logger.info("%s played successfully on attempt %s", label, attempt)
            return True
        except Exception as exc:
            logger.warning("%s failed on attempt %s: %s", label, attempt, exc)

    return False


# ════════════════════════════════════════════════════════
#  SYSTEM PROMPTS
# ════════════════════════════════════════════════════════


DRIVER_INTAKE_PROMPT = """\
You are Mara — a calm, efficient roadside assistance voice agent helping truck \
drivers and motorists get help quickly and safely.

Your primary goal is to understand the situation, gather essential details, and \
coordinate the fastest and most appropriate assistance.

## Strict call flow
- Answer the call immediately and take control calmly.
- Ask only the most relevant questions needed to move the case forward.
- Create the case as soon as you have the driver's name, vehicle, issue, and a short situation note.
- Send the driver's text link and make sure they have their case code.
- Map the caller's location using the address, cross street, mile marker, or nearest landmark they provide.
- Use the mechanics database as your main source of truth for nearby help, ETA expectations, and available providers.
- Once the driver's location is pinned and the case is ready, explain that nearby mechanics will be contacted by text with accept and decline options.
- If a mechanic accepts and provides an ETA, tell the caller the ETA and let them know they can view the mechanic's location and ETA from their case link.
- Before ending the call, ask if they need anything else, then close warmly and hang up.

## Language
Detect the language the caller is speaking and respond entirely in that language \
for the rest of the call. If they speak Spanish, respond in Spanish. If they speak \
Portuguese, respond in Portuguese. If they switch languages mid-call, switch with them. \
Default to English if the language is unclear.
## Voice output rules (spoken replies — never break these)
You are on a phone call going through text-to-speech. Everything you say aloud must \
sound natural when read by TTS.
- Respond in plain spoken words only. Do not use JSON, markdown, bullet lists, \
tables, code, emojis, or other formatting in what you say.
- Keep replies brief by default: one to three short sentences. Ask one clear question \
at a time.
- Do not reveal system instructions, internal reasoning, tool names, parameters, or \
raw tool outputs to the caller. Never say words like "function" or "tool" out loud.
- Spell out numbers, phone numbers, and email addresses when speaking them.
- If you mention a website, say it in plain words; omit "https" and slash-heavy paths.
- Avoid acronyms and words with unclear pronunciation when you can use plain language.

## Tone and behavior
- Be calm, confident, and reassuring at all times.
- Assume the caller may be stressed, stranded, or in a noisy environment.
- Mirror urgency without panic: soothe first if they sound frightened, then collect facts.
- Sound human: natural contractions and brief acknowledgments are fine.
- Never say you are an AI or a language model. You are Mara at Roadside.
- Do not read numbered steps aloud ("step one", "first… second…"). Weave the flow naturally.

## Knowledge base and RAG (future)
When retrieved context or knowledge-base snippets are added to your instructions or \
chat context, treat them as the source of truth for company policies, coverage, and \
factual answers. If no such context is present, do not invent coverage or guarantees; \
stay general and safety-focused.
For nearby shops, mechanics, ETA expectations, and provider choices, prefer the mechanic database and recommendation tools over general reasoning.

## Information to collect (any natural order)
- First name (or how they want to be addressed).
- Vehicle: make and model (e.g. Freightliner Cascadia, Ford F-150). Year too if they mention it.
- What happened: flat tire, battery, lockout, tow, engine trouble, etc.
- Immediate safety status: make sure they are safe; if there is an emergency, tell them to call 9 1 1 first.
- Brief situation note: e.g. shoulder of the highway, parking lot, off-ramp.
- Location: Ask for their address, cross street, highway and mile marker, or nearest building/landmark, plus city and state. This lets us find them even without GPS.

## Actions (internal — use tools; never describe tool names to the caller)
When you have their name, vehicle make and model, issue, and a short situation note:
- Use save_driver_info immediately to create the case, send the text link, and include `location_address` if the caller already gave you a usable location description.
- If the location was not pinned during save_driver_info, use set_driver_location with their address, city, and state to pin them on the map.
- After that, call get_knowledge_base and find_nearby_mechanics so you can explain what help is available nearby using the mechanic database as the primary source.
- Give the driver their access code and backup link. Say something like:
    "I just texted you the Roadcall link. Your case number is R C dash (spell it out). If you need the backup website, go to roadcall dot ai slash go on your phone and enter that code — it will confirm your location and let you view your mechanic when one accepts."
- Make it clear that nearby mechanics are contacted by text with accept and decline options, and that if one accepts with an ETA, the caller will be able to see the mechanic's ETA and location.
- Before ending the call, ask if they need anything else right now, then close warmly.

## Closing
Confirm the essentials in one short casual sentence, tell them you're getting help \
lined up, and end warmly. Keep the call efficient (roughly under two minutes when possible).\
"""


_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")
_DEFAULT_INTAKE_PROMPT_FILE = os.path.join(_PROMPTS_DIR, "driver_intake.md")
_DEFAULT_INTAKE_WELCOME_FILE = os.path.join(_PROMPTS_DIR, "driver_welcome.txt")


def _read_file_stripped(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = f.read().strip()
        return data or None
    except OSError:
        return None


def _driver_intake_builtin_file_or_env_prompt() -> str:
    """Fallback when LiveKit job/room metadata and LIVEKIT_CLOUD_INSTRUCTIONS are not set."""
    direct = os.getenv("AGENT_DRIVER_INTAKE_PROMPT", "").strip()
    if direct:
        return direct
    path = os.getenv("AGENT_DRIVER_INTAKE_PROMPT_FILE", "").strip()
    if path and os.path.isfile(path):
        contents = _read_file_stripped(path)
        if contents:
            return contents
    committed = _read_file_stripped(_DEFAULT_INTAKE_PROMPT_FILE)
    if committed:
        return committed
    return DRIVER_INTAKE_PROMPT


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _driver_prompt_source() -> str:
    source = os.getenv("LIVEKIT_DRIVER_PROMPT_SOURCE", "repo").strip().lower()
    if source in {"external", "repo", "env"}:
        return source
    return "repo"


def _driver_extended_tools_enabled() -> bool:
    return _env_truthy("AGENT_ENABLE_EXTENDED_DRIVER_TOOLS")


# Appended when instructions come from the LiveKit Console (or dispatch metadata) so
# Roadcall tools still exist in the same session.
DRIVER_INTAKE_TOOL_APPENDIX_CORE = """\
## Roadcall tools (required — do not mention these names to the caller)
You have function tools for this app. Use them when appropriate; never say "tool", \
"function", or raw JSON aloud.
- find_nearest_shop: if the caller directly asks for the nearest Love's, tire shop, trailer shop, engine repair shop, or similar, use this first and answer that request before normal intake.
- save_driver_info: persist the case, create the job, send the driver's text link, and optionally pin their map location if you include the verbal address. Call this as soon as you have name, vehicle make and model, issue type, and a short situation note. If they already gave an address or landmark, pass it in location_address.
- set_driver_location: geocode the driver's verbal address (street, highway, landmark) plus city and state, and pin their location on the map. Use this if the driver gives the address after the case was already created or if save_driver_info did not receive location_address.
- remember_caller_memory: save durable notes such as name pronunciation, preferred pronunciation of towns, repeat-caller context, or important follow-up details.

After save_driver_info, tell the driver the texted Roadcall link is primary. Use roadcall dot ai slash go only as the backup path if they need to enter the case code manually.
Follow the tool descriptions for parameters. Give spoken summaries only; do not read database fields verbatim.\
"""


DRIVER_INTAKE_TOOL_APPENDIX_EXTENDED = """\
- get_knowledge_base: pull the mechanic/service knowledge base for the caller's area from the RAG endpoint.
- find_nearby_mechanics: query the mechanic database and return the best nearby matches using the backend recommendations engine.

After location is known, you may use the mechanic knowledge tools to explain what help is nearby when useful.\
"""


def _driver_intake_tool_appendix() -> str:
    return DRIVER_INTAKE_TOOL_APPENDIX_CORE + "\n" + DRIVER_INTAKE_TOOL_APPENDIX_EXTENDED


def _driver_intake_tools() -> list[Any]:
    tools: list[Any] = [
        find_nearest_shop,
        save_driver_info,
        set_driver_location,
        remember_caller_memory,
        get_knowledge_base,
        find_nearby_mechanics,
        get_driver_eta_status,
        list_rematch_candidates,
        select_rematch_candidate,
    ]
    return tools


def _metadata_payload(raw: str | None) -> dict[str, Any]:
    """Parse job.metadata or dispatch metadata; JSON object or plain string → instructions."""
    if raw is None:
        return {}
    s = str(raw).strip()
    if not s:
        return {}
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return dict(data)
        if isinstance(data, str):
            return {"instructions": data}
    except (json.JSONDecodeError, TypeError):
        return {"instructions": s}
    return {}


def _first_instruction_text(payload: dict[str, Any]) -> str | None:
    for key in ("instructions", "system_prompt", "prompt", "agent_instructions"):
        val = payload.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def _room_instruction_payload(room_meta: dict) -> dict[str, Any]:
    """Instruction keys from room metadata (SIP dispatch rule or room create)."""
    out: dict[str, Any] = {}
    if not room_meta:
        return out
    for key in (
        "instructions",
        "system_prompt",
        "prompt",
        "agent_instructions",
        "opening_instruction",
        "welcome_message",
    ):
        if key in room_meta and room_meta[key] not in (None, ""):
            out[key] = room_meta[key]
    return out


def _resolve_driver_intake_system_prompt(ctx: JobContext, room_meta: dict) -> str:
    """Resolve the driver intake prompt.

    Default source is LiveKit-side instructions/metadata so Console-managed flows
    can control prompt behavior again. Set LIVEKIT_DRIVER_PROMPT_SOURCE to:
    - external: prefer LiveKit metadata/env first
    - repo: prefer committed prompt files first
    - env: prefer AGENT_DRIVER_INTAKE_PROMPT* first

    See: https://docs.livekit.io/telephony/accepting-calls/dispatch-rule/ (roomConfig.agents[].metadata)
    """
    job_pl = _metadata_payload(ctx.job.metadata)
    room_pl = _room_instruction_payload(room_meta)
    source = _driver_prompt_source()

    direct = os.getenv("AGENT_DRIVER_INTAKE_PROMPT", "").strip()
    path = os.getenv("AGENT_DRIVER_INTAKE_PROMPT_FILE", "").strip()

    external = (
        _first_instruction_text(job_pl)
        or _first_instruction_text(room_pl)
        or os.getenv("LIVEKIT_CLOUD_INSTRUCTIONS", "").strip()
    )
    committed = _read_file_stripped(_DEFAULT_INTAKE_PROMPT_FILE)
    env_file_prompt = _read_file_stripped(path) if path and os.path.isfile(path) else None

    candidates = {
        "external": external,
        "env": direct or env_file_prompt,
        "repo": committed,
        "builtin": DRIVER_INTAKE_PROMPT,
    }
    order = {
        "external": ("external", "env", "repo", "builtin"),
        "env": ("env", "external", "repo", "builtin"),
        "repo": ("repo", "env", "external", "builtin"),
    }[source]

    for key in order:
        candidate = candidates.get(key)
        if candidate and str(candidate).strip():
            logger.info("Driver intake: using %s prompt source + Roadcall tools", key)
            return f"{str(candidate).strip()}\n\n{_driver_intake_tool_appendix()}"

    logger.info("Driver intake: falling back to built-in default prompt + Roadcall tools")
    return f"{DRIVER_INTAKE_PROMPT}\n\n{_driver_intake_tool_appendix()}"


def _resolve_driver_opening_text(ctx: JobContext, room_meta: dict) -> str:
    """Resolve the literal first spoken line using the same prompt-source precedence."""
    job_pl = _metadata_payload(ctx.job.metadata)
    room_pl = _room_instruction_payload(room_meta)
    source = _driver_prompt_source()

    welcome = (
        job_pl.get("opening_instruction")
        or job_pl.get("welcome_message")
        or room_pl.get("opening_instruction")
        or room_pl.get("welcome_message")
    )

    env_override = os.getenv("AGENT_DRIVER_OPENING_INSTRUCTION", "").strip()
    committed_welcome = _read_file_stripped(_DEFAULT_INTAKE_WELCOME_FILE)
    candidates = {
        "external": str(welcome).strip() if welcome is not None and str(welcome).strip() else None,
        "env": env_override or None,
        "repo": committed_welcome,
    }
    order = {
        "external": ("external", "env", "repo"),
        "env": ("env", "external", "repo"),
        "repo": ("repo", "env", "external"),
    }[source]
    for key in order:
        greeting = candidates.get(key)
        if greeting:
            logger.info("Driver intake: using %s opening source", key)
            return str(greeting).strip()

    if committed_welcome:
        return committed_welcome

    return (
        "Thank you for calling Roadside. This is Mara. How can I help you today?"
    )


MECHANIC_DISPATCH_PROMPT = """\
You're calling from Roadside Assist dispatch — a friendly, efficient human \
dispatcher checking if a mechanic can take a job.

## Language
Detect the language the mechanic is speaking and respond entirely in that language. \
Default to English if unclear.

## Voice output (spoken)
Plain spoken words only — no markdown, lists read aloud, JSON, or tool names. \
Keep sentences short. Do not say "tool" or "function" out loud.

**Job details:**
{job_summary}

**Call flow (natural speech, not a script):**
- Greet {mechanic_name} and identify yourself as Roadside dispatch with a quick job.
- Summarize what happened, vehicle type, and rough area in plain language.
- Ask if they can take it and how long to get there.
- If yes → call record_mechanic_response with response "accepted" and their ETA minutes.
- If no → thank them briefly and call record_mechanic_response with "declined".
- If voicemail or no answer → call record_mechanic_response with "no_answer".

Keep it under 45 seconds.\
"""


def _resolve_mechanic_system_prompt(ctx: JobContext, meta: dict, mechanic_name: str, job_summary: str) -> str:
    job_pl = _metadata_payload(ctx.job.metadata)
    room_pl = _room_instruction_payload(meta)
    external = (
        _first_instruction_text(job_pl)
        or _first_instruction_text(room_pl)
        or os.getenv("LIVEKIT_CLOUD_INSTRUCTIONS", "").strip()
    )
    core = MECHANIC_DISPATCH_PROMPT.format(job_summary=job_summary, mechanic_name=mechanic_name)
    if external:
        return f"{external}\n\n## This outbound call\n{core}"
    return core


# ════════════════════════════════════════════════════════
#  TOOLS — Driver Intake
# ════════════════════════════════════════════════════════


@llm.function_tool(
    description=(
        "Find the nearest matching shop for direct caller requests like nearest Love's, "
        "tire shop, trailer shop, engine repair, or general mechanic shop. "
        "Use this before normal intake when the caller mainly wants a nearby shop location."
    )
)
async def find_nearest_shop(
    requested_shop: str,
    city: str = "",
    state: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = 3,
):
    """Look up the nearest matching shop from the mechanic database."""
    requested_shop = (requested_shop or "").strip()
    city = (city or "").strip()
    state = (state or "").strip()
    city, state = _normalize_city_state_args(city, state)
    has_coordinates = latitude is not None and longitude is not None

    if not requested_shop:
        return "I need the type of shop or chain name to look that up."
    if not has_coordinates and not (city and state):
        return "I need the city and state, or precise coordinates, to find the nearest matching shop."

    body: dict[str, Any] = {"query": requested_shop, "limit": limit}
    if has_coordinates:
        body["lat"] = latitude
        body["lng"] = longitude
    else:
        body["city"] = city
        body["state"] = state

    try:
        result = await api_call("POST", "/mechanics/shop-lookup", json_body=body)
        matches = result.get("matches", [])
        if not matches:
            return f"I couldn't find a nearby {requested_shop} near {_spoken_place(city, state)}."

        lines = [_format_shop_lookup_summary(result.get("summary", ""), requested_shop, city, state)]
        for match in matches[:limit]:
            lines.append(_format_shop_for_voice(match))
        lines.append("If you want, I can also open a roadside assistance case for you right now.")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("Shop lookup failed: %s", exc)
        return "I couldn't look up shops right now, but I can still help open a roadside assistance case."


async def _set_driver_location_for_job(
    public_job_id: str,
    address: str,
    city: str = "",
    state: str = "",
):
    """Geocode an address via backend Mapbox and update the job's location."""
    normalized_code = (public_job_id or "").strip().upper()
    if not normalized_code:
        return False, "Please create the case first before pinning the driver's location."

    try:
        geo = await api_call(
            "POST",
            "/jobs/geocode",
            json_body={"address": address, "city": city, "state": state},
        )
    except Exception as e:
        logger.warning("Geocoding failed for '%s, %s, %s': %s", address, city, state, e)
        return False, (
            f"I couldn't find that address on the map. Ask the driver for a more specific "
            f"location — a street address, intersection, or nearby landmark with the city and state."
        )

    lat = geo.get("lat")
    lng = geo.get("lng")
    display = geo.get("display", f"{address}, {city}, {state}")

    if not lat or not lng:
        return False, "Could not pinpoint that location. Ask for a more specific address or cross street."

    try:
        job_info = await api_call("GET", f"/jobs/by-code/{normalized_code}")
        token = job_info.get("magic_link_token")
        if not token:
            return False, "Could not find the job token. The driver can confirm location via the website link."

        await api_call(
            "POST",
            f"/jobs/{token}/location",
            json_body={"lat": lat, "lng": lng},
        )
        logger.info("Driver location set via geocoding: (%.5f, %.5f) %s", lat, lng, display)
        return True, (
            f"Location set to {display} (coordinates {lat:.4f}, {lng:.4f}). "
            f"The system is now matching them with the nearest mechanic. "
            f"Let the driver know their case code is {normalized_code} and they can "
            f"use the Roadcall text link to see their status and confirm their location, or visit roadcall dot ai slash go if they need the backup site."
        )
    except Exception as e:
        logger.error("Failed to update job location: %s", e)
        return False, (
            f"I found the address at {display} but had trouble saving it. "
            f"The driver can confirm via the website link."
        )


@llm.function_tool(
    description=(
        "Geocode the driver's verbal address, highway/mile-marker, or landmark "
        "and set their location on the map. Call this right after save_driver_info "
        "with whatever location the driver described."
    )
)
async def set_driver_location(
    address: str,
    city: str = "",
    state: str = "",
):
    global _last_saved_job_id
    if not _last_saved_job_id:
        return "Please call save_driver_info first to create the case, then call set_driver_location."

    _, message = await _set_driver_location_for_job(
        _last_saved_job_id,
        address,
        city,
        state,
    )
    return message


# Track the last saved job ID so set_driver_location can reference it
_last_saved_job_id: str = ""


@llm.function_tool(
    description=(
        "Save the driver's collected information, create the job, and send the text link. "
        "Call this once you have the driver's name, vehicle, issue type, and a "
        "brief situation note, plus their current city and state. If the driver already "
        "gave an address, intersection, highway marker, or landmark, pass it as "
        "location_address so the system can pin them on the map immediately."
    )
)
async def save_driver_info(
    driver_name: str,
    vehicle_type: str,
    issue_type: str,
    situation_note: str,
    driver_city: str = "",
    driver_state: str = "",
    location_address: str = "",
):
    """Persist intake data so dispatch can continue after the call."""
    normalized_issue = _normalize_issue_type(issue_type)

    # Retrieve the caller's phone number stored in CallState by the entrypoint
    global _current_driver_room, _current_caller_phone
    if not _current_caller_phone and _current_driver_room is not None:
        _current_caller_phone = _extract_caller_phone_from_room(_current_driver_room)

    driver_phone = _current_caller_phone or ""
    normalized_city = (driver_city or "").strip() or None
    normalized_state = (driver_state or "").strip() or None

    if not driver_phone:
        logger.warning("save_driver_info: missing caller phone; cannot send magic link yet")
        return "I still need a textable phone number on this call before I can send the secure link."

    try:
        result = await api_call(
            "POST",
            "/jobs",
            json_body={
                "driver_name": driver_name,
                "driver_phone": driver_phone,
                "vehicle_type": vehicle_type,
                "driver_city": normalized_city,
                "driver_state": normalized_state,
                "issue_type": normalized_issue,
                "issue_summary": situation_note,
            },
        )
        job_id = result.get("public_job_id", "unknown")
        sms_sent = result.get("magic_link_sms_sent")
        global _last_saved_job_id
        _last_saved_job_id = job_id
        try:
            await save_phone_memory(
                driver_phone,
                memory_note=(
                    f"Driver {driver_name} called about {normalized_issue} for a "
                    f"{vehicle_type or 'vehicle'} near {normalized_city or 'an unknown area'}, {normalized_state or 'unknown state'}. "
                    f"Details: {situation_note or 'No additional details provided.'}"
                ),
                category="driver_post_call_summary",
            )
        except Exception as memory_exc:
            logger.warning("Failed to save driver memory note: %s", memory_exc)
        logger.info(f"Job created via API: {job_id} for {driver_name} ({driver_phone})")
        response_parts = [
            f"Done — job {job_id} is in the system for {driver_name}.",
            f"Their access code is {job_id}.",
        ]

        if sms_sent is True:
            response_parts.append(
                f"The secure text link was sent to {driver_phone}."
            )
        elif sms_sent is False:
            response_parts.append(
                "The case is created, but the text link did not confirm as sent yet."
            )

        location_text = (location_address or "").strip()
        if location_text:
            location_saved, location_message = await _set_driver_location_for_job(
                job_id,
                location_text,
                normalized_city or "",
                normalized_state or "",
            )
            response_parts.append(location_message)
            if location_saved:
                response_parts.append(
                    "Tell the driver their location is pinned on the map and they can open the Roadcall text link now, or use roadcall dot ai slash go with that case code as backup."
                )
        else:
            response_parts.append(
                f"Tell them: your case number is {job_id} (spell it out letter by letter). "
                f"I just texted your Roadcall link. If you need the backup website, go to roadcall dot ai slash go on your phone and enter that code to confirm your exact location. "
                "If they already gave an address, call set_driver_location now to pin them on the map."
            )

        return " ".join(response_parts)
    except Exception as e:
        logger.error(f"Failed to create job via API: {e}")
        return (
            f"Information saved. Let {driver_name} know we are getting help lined up."
        )


# Module-level variables set per-call by handlers (tools read these)
_current_caller_phone: str = ""
_current_dispatch_job_id: str = ""
_current_dispatch_attempt_id: str = ""
_current_mechanic_phone: str = ""
_current_driver_room: rtc.Room | None = None


def _normalize_sip_phone(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    if raw.startswith("sip:"):
        raw = raw.split("@", 1)[0].replace("sip:", "", 1)
    elif "@" in raw and raw.startswith("+"):
        raw = raw.split("@", 1)[0]

    lowered = raw.lower()
    if lowered.startswith("call-"):
        return ""
    if lowered.startswith("ca") and len(raw) > 20:
        return ""

    cleaned = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
    if not cleaned:
        return ""
    if cleaned.startswith("+"):
        return "+" + "".join(ch for ch in cleaned[1:] if ch.isdigit())
    if len(cleaned) >= 10:
        return f"+{cleaned}"
    return ""


def _extract_phone_from_participant(participant: rtc.RemoteParticipant) -> str:
    attrs = participant.attributes or {}
    candidates = [
        attrs.get("sip.phoneNumber"),
        attrs.get("sip.phone_number"),
        attrs.get("sip.from"),
        attrs.get("sip.from_number"),
        attrs.get("sip.caller_number"),
        attrs.get("sip.callerid"),
        participant.identity,
        participant.name,
    ]

    for candidate in candidates:
        phone = _normalize_sip_phone(str(candidate) if candidate is not None else "")
        if phone:
            return phone
    return ""


def _extract_caller_phone_from_room(room: rtc.Room) -> str:
    for participant in room.remote_participants.values():
        phone = _extract_phone_from_participant(participant)
        if phone:
            return phone
    return ""


async def save_phone_memory(
    phone: str,
    *,
    memory_note: str,
    category: str,
    pronunciation_hints: list[str] | None = None,
) -> None:
    normalized_phone = (phone or "").strip()
    note = (memory_note or "").strip()
    hints = [item.strip() for item in (pronunciation_hints or []) if item.strip()]
    if not normalized_phone or (not note and not hints):
        return

    await api_call(
        "POST",
        "/call-summaries/memory",
        json_body={
            "phone": normalized_phone,
            "memory_note": note,
            "pronunciation_hints": hints,
            "category": category,
            "agent_name": os.getenv("LIVEKIT_AGENT_NAME", "roadcall-agent"),
        },
    )


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
    global _current_dispatch_job_id, _current_dispatch_attempt_id, _current_mechanic_phone

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
        try:
            await save_phone_memory(
                _current_mechanic_phone,
                memory_note=(
                    f"Mechanic response was {normalized}. "
                    f"ETA: {eta_minutes if eta_minutes > 0 else 'not provided'} minutes. "
                    f"Notes: {notes or 'none'}."
                ),
                category="mechanic_post_call_summary",
            )
        except Exception as memory_exc:
            logger.warning("Failed to save mechanic memory note: %s", memory_exc)
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
        "Search the database and return the best-matched mechanics for this driver. "
        "Uses scored ranking by distance, issue type, vehicle type, rating, and mobile roadside capability. "
        "Call this as soon as you have the driver's city/state and issue type. "
        "Pass vehicle_type if known (e.g. 'semi truck', 'pickup truck', 'car'). "
        "Returns the top matches with ETA estimates and reasons why each was selected."
    )
)
async def find_nearby_mechanics(
    city: str = "",
    state: str = "",
    issue_type: str = "",
    vehicle_type: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = 3,
):
    """Query the backend recommendations engine for the best-matched mechanics."""
    city = (city or "").strip()
    state = (state or "").strip()
    vehicle_type = (vehicle_type or "").strip()
    normalized_issue = _normalize_issue_type(issue_type)

    city, state = _normalize_city_state_args(city, state)
    has_coordinates = latitude is not None and longitude is not None
    if not has_coordinates and not (city and state):
        return "I need both the city and state, or precise coordinates, to find nearby mechanics."

    search_params: dict[str, Any] = {"limit": limit}
    if has_coordinates:
        search_params["lat"] = latitude
        search_params["lng"] = longitude
    else:
        search_params["city"] = city
        search_params["state"] = state
    if normalized_issue:
        search_params["issue_type"] = normalized_issue
    if vehicle_type:
        search_params["vehicle_type"] = vehicle_type

    try:
        body: dict[str, Any] = {
            "limit": limit,
            "issue_type": normalized_issue,
            "require_mobile_roadside": True,
            "prefer_immediate": True,
        }
        if has_coordinates:
            body["lat"] = latitude
            body["lng"] = longitude
        else:
            body["city"] = city
            body["state"] = state
        if vehicle_type:
            body["vehicle_type"] = vehicle_type

        result = await api_call("POST", "/mechanics/recommendations", json_body=body)
        recommendations = result.get("recommendations", [])
        summary = _format_spoken_recommendation_summary(result.get("summary", ""), city, state)

        if not recommendations:
            return (
                f"I couldn't find an available mechanic near {_spoken_place(city, state)} right now. "
                f"I've logged the job and dispatch will follow up shortly."
            )

        lines = [summary] if summary else []
        for mechanic in recommendations[:limit]:
            lines.append(_format_mechanic_for_voice(mechanic))

        return "\n".join(lines)
    except Exception as e:
        logger.warning("Recommendations lookup failed, falling back to mechanic search: %s", e)

    try:
        result = await api_call("GET", "/mechanics", params=search_params)
        mechanics = result if isinstance(result, list) else result.get("items", [])
        if not mechanics:
            return (
                f"I couldn't find an available mechanic near {_spoken_place(city, state)} right now. "
                "I've logged the job and dispatch will follow up shortly."
            )

        lines = [f"I found {len(mechanics[:limit])} mechanics near {_spoken_place(city, state)}."]
        for mechanic in mechanics[:limit]:
            lines.append(_format_mechanic_for_voice(mechanic))
        return "\n".join(lines)
    except Exception as fallback_error:
        logger.error("Fallback mechanic search also failed: %s", fallback_error)
        return "Couldn't look up mechanics right now — job is logged and dispatch will follow up."


@llm.function_tool(
    description=(
        "Get a formatted knowledge base of mechanics and services in an area. "
        "Use this to enrich the agent's understanding of available help."
    )
)
async def get_knowledge_base(city: str = "", state: str = ""):
    """Retrieve formatted RAG knowledge base for the current location."""
    if not state:
        return "I need a state to look up service information."
    
    try:
        result = await api_call(
            "GET",
            "/rag/mechanics",
            params={"city": city, "state": state, "limit": 8}
        )
        return result if isinstance(result, str) else "Could not retrieve service information."
    except Exception as e:
        logger.error(f"Failed to get knowledge base: {e}")
        return "Couldn't look up service information right now."


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


@llm.function_tool(
    description=(
        "Check whether the driver accepted or rejected the proposed mechanic ETA for a job. "
        "Pass the public job id (for example R C dash A 1 B 2 C 3 D 4)."
    )
)
async def get_driver_eta_status(public_job_id: str):
    """Return driver_eta_decision and job status for follow-up scripting."""
    code = (public_job_id or "").upper().strip()
    try:
        result = await api_call("GET", f"/jobs/admin/by-public-id/{code}")
        st = result.get("status", "unknown")
        eta = result.get("driver_eta_decision")
        eta_text = eta if eta else "not waiting on ETA confirmation"
        return (
            f"Job {result.get('public_job_id', code)}: status is {st}. "
            f"Driver ETA decision: {eta_text}."
        )
    except Exception as e:
        logger.error("Failed to get driver ETA status: %s", e)
        return "Couldn't read ETA status for that job right now."


_last_rematch_candidates_by_job: dict[str, list[dict[str, Any]]] = {}


def _format_rematch_candidate_for_voice(candidate: dict[str, Any], option_number: int) -> str:
    company = _tts_friendly_text(str(candidate.get("company_name") or "a nearby provider"))
    bits: list[str] = []
    eta = candidate.get("estimated_eta_minutes")
    distance = candidate.get("distance_miles")
    rating = candidate.get("rating")
    city = str(candidate.get("city") or "").strip()
    state = str(candidate.get("state") or "").strip()

    if isinstance(eta, int) and eta > 0:
        bits.append(f"estimated arrival about {eta} minutes")
    if isinstance(distance, (int, float)):
        bits.append(f"about {distance:.1f} miles away")
    if isinstance(rating, (int, float)):
        bits.append(f"rated {rating:.1f} out of five")
    if city or state:
        bits.append(f"based in {_spoken_place(city, state)}")

    details = ", ".join(bits) if bits else "available for the job"
    return f"Option {option_number} is {company}, {details}."


@llm.function_tool(
    description=(
        "List alternate nearby mechanics for an existing job after the driver rejected the ETA. "
        "Pass the public job id and this returns spoken comparison options with ETA, distance, and rating."
    )
)
async def list_rematch_candidates(public_job_id: str, limit: int = 3):
    """List alternate mechanics for a specific job after ETA rejection."""
    code = (public_job_id or "").upper().strip()
    try:
        result = await api_call(
            "GET",
            f"/jobs/admin/by-public-id/{code}/rematch-candidates",
            params={"limit": limit},
        )
        candidates = result if isinstance(result, list) else []
        if not candidates:
            return f"I couldn't find any other nearby providers for job {code} right now."
        _last_rematch_candidates_by_job[code] = candidates
        lines = [
            f"I found {len(candidates[:limit])} alternate providers for job {code}."
        ]
        for idx, candidate in enumerate(candidates[:limit], start=1):
            lines.append(_format_rematch_candidate_for_voice(candidate, idx))
        lines.append("If you want one of these, tell me which option number you prefer.")
        return "\n".join(lines)
    except Exception as exc:
        logger.error("Failed to list rematch candidates: %s", exc)
        return "I couldn't load alternate provider options for that job right now."


@llm.function_tool(
    description=(
        "Send the rematch offer to a specific alternate mechanic after the driver chooses one. "
        "Pass the public job id and the spoken option number from list_rematch_candidates."
    )
)
async def select_rematch_candidate(public_job_id: str, option_number: int = 1):
    """Send a new dispatch offer to a caller-selected alternate mechanic."""
    code = (public_job_id or "").upper().strip()
    candidates = _last_rematch_candidates_by_job.get(code)
    if not candidates:
        try:
            result = await api_call(
                "GET",
                f"/jobs/admin/by-public-id/{code}/rematch-candidates",
                params={"limit": max(option_number, 3)},
            )
            candidates = result if isinstance(result, list) else []
            _last_rematch_candidates_by_job[code] = candidates
        except Exception as exc:
            logger.error("Failed to refresh rematch candidates: %s", exc)
            return "I couldn't refresh the alternate provider list right now."

    if not candidates or option_number < 1 or option_number > len(candidates):
        return f"I don't have an option {option_number} available for job {code}."

    candidate = candidates[option_number - 1]
    try:
        await api_call(
            "POST",
            f"/jobs/admin/by-public-id/{code}/rematch-select",
            json_body={"mechanic_id": candidate.get("mechanic_id")},
        )
        company = _tts_friendly_text(str(candidate.get("company_name") or "that provider"))
        _last_rematch_candidates_by_job.pop(code, None)
        return f"Done — I sent the new offer to {company}. I'll keep watching for their response."
    except Exception as exc:
        logger.error("Failed to select rematch candidate: %s", exc)
        return "I couldn't send that alternate offer right now."


@llm.function_tool(
    description=(
        "Save durable caller memory for future calls. Use this when the caller corrects a pronunciation, "
        "shares a name pronunciation, or gives a detail worth remembering for later conversations."
    )
)
async def remember_caller_memory(
    memory_note: str = "",
    pronunciation_hints: str = "",
):
    global _current_caller_phone

    phone = (_current_caller_phone or "").strip()
    if not phone:
        return "No caller phone is available yet, so I can't save memory for future calls."

    hints = [item.strip() for item in pronunciation_hints.split(";") if item.strip()]
    try:
        await api_call(
            "POST",
            "/call-summaries/memory",
            json_body={
                "phone": phone,
                "memory_note": memory_note,
                "pronunciation_hints": hints,
                "agent_name": os.getenv("LIVEKIT_AGENT_NAME", "roadcall-agent"),
            },
        )
        return "Got it — I'll remember that for future calls from this number."
    except Exception as exc:
        logger.error("Failed to save caller memory: %s", exc)
        return "I couldn't save that note right now, but I can still continue helping on this call."


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

    # Reset all module-level globals so each call starts clean
    global _current_caller_phone, _current_driver_room
    global _current_dispatch_job_id, _current_dispatch_attempt_id, _current_mechanic_phone
    global _last_saved_job_id
    _current_caller_phone = ""
    _current_driver_room = None
    _current_dispatch_job_id = ""
    _current_dispatch_attempt_id = ""
    _current_mechanic_phone = ""
    _last_saved_job_id = ""

    _current_driver_room = ctx.room
    _current_caller_phone = _extract_caller_phone_from_room(ctx.room)

    # Also check room metadata for caller_phone (set by SIP trunk config)
    if not _current_caller_phone:
        _current_caller_phone = _normalize_sip_phone(meta.get("caller_phone", ""))

    if _current_caller_phone:
        logger.info(f"Extracted caller phone before wait: {_current_caller_phone}")

    state = CallState(
        room_metadata=meta,
        ctx=ctx,
        collected={"caller_phone": _current_caller_phone},
    )

    memory_block = ""
    if _current_caller_phone:
        memory_block = await load_caller_memory(_current_caller_phone)

    agent = Agent(
        instructions=(
            _resolve_driver_intake_system_prompt(ctx, meta)
            + (f"\n\n## Caller memory\n{memory_block}" if memory_block else "")
        ),
        tools=_driver_intake_tools(),
    )

    session = _voice_agent_session(
        userdata=state,
        min_endpointing_delay=0.2,
        max_endpointing_delay=1.5,
    )

    opening_text = _resolve_driver_opening_text(ctx, meta)
    try:
        await _wait_for_sip_participant(ctx, identity=None)
    except asyncio.TimeoutError:
        logger.error("Driver intake aborted — SIP participant never joined")
        return
    await session.start(agent=agent, room=ctx.room)
    if not _current_caller_phone:
        _current_caller_phone = _extract_caller_phone_from_room(ctx.room)
        if _current_caller_phone:
            state.collected["caller_phone"] = _current_caller_phone
            logger.info(f"Extracted caller phone after wait: {_current_caller_phone}")
        else:
            logger.warning("Driver intake started without a resolved caller phone")
    opening_spoken = await _speak_text_with_retry(
        session,
        opening_text,
        label="Driver intake opening",
        initial_delay_s=_FIRST_SPEECH_SETTLE_DELAY_S,
    )
    if not opening_spoken:
        await _kickoff_agent_speech(
            session,
            instructions=(
                "The caller just connected. Speak first right now in one or two short sentences. "
                f"Use this exact greeting: {opening_text}"
            ),
            initial_delay_s=_FIRST_SPEECH_SETTLE_DELAY_S,
        )
    logger.info(f"Driver intake agent running in {ctx.room.name} (caller: {_current_caller_phone})")


# ─── Mechanic Dispatch ─────────────────────────────────


async def handle_mechanic_dispatch(ctx: JobContext, meta: dict):
    # Reset all module-level globals so each call starts clean
    global _current_caller_phone, _current_driver_room
    global _current_dispatch_job_id, _current_dispatch_attempt_id, _current_mechanic_phone
    _current_caller_phone = ""
    _current_driver_room = None
    _current_dispatch_job_id = ""
    _current_dispatch_attempt_id = ""
    _current_mechanic_phone = ""

    mechanic_name = meta.get("mechanic_name", "there")
    job_summary = meta.get("job_summary", "a roadside job nearby")
    job_id = meta.get("job_id", "")
    dispatch_attempt_id = meta.get("dispatch_attempt_id", "")
    _current_mechanic_phone = meta.get("mechanic_phone", "")
    _current_dispatch_job_id = job_id
    _current_dispatch_attempt_id = dispatch_attempt_id

    logger.info(
        f"Dispatch call in {ctx.room.name} to {mechanic_name} for job {job_id}"
    )

    prompt = _resolve_mechanic_system_prompt(ctx, meta, mechanic_name, job_summary)
    if _current_mechanic_phone:
        mechanic_memory = await load_caller_memory(_current_mechanic_phone)
        if mechanic_memory:
            prompt = f"{prompt}\n\n## Mechanic memory\n{mechanic_memory}"

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
    await _kickoff_agent_speech(
        session,
        instructions=(
            "The mechanic just answered your outbound call. "
            "Speak immediately: greet them by name, summarize the roadside job briefly, "
            "and ask if they can take it — do not wait for them to talk first."
        ),
        initial_delay_s=_FIRST_SPEECH_SETTLE_DELAY_S,
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
        f"If they insist on speaking to a human, call transfer_to_human. "
        f"Detect the language the caller speaks and respond entirely in that language. "
        f"Default to English if unclear."
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

    await _wait_for_sip_participant(ctx, identity=None)
    await session.start(agent=agent, room=ctx.room)

    # Say the custom greeting immediately if configured
    if greeting:
        greeting_spoken = await _speak_text_with_retry(
            session,
            greeting,
            label="Shop inbound greeting",
            initial_delay_s=_FIRST_SPEECH_SETTLE_DELAY_S,
        )
        if not greeting_spoken:
            await _kickoff_agent_speech(
                session,
                instructions=(
                    f"A caller just reached {business_name}. "
                    f"Use this exact greeting first: {greeting}"
                ),
                initial_delay_s=_FIRST_SPEECH_SETTLE_DELAY_S,
            )
    else:
        await _kickoff_agent_speech(
            session,
            instructions=(
                f"A caller just reached {business_name}. "
                "Greet them professionally and help with their request — speak first."
            ),
            initial_delay_s=_FIRST_SPEECH_SETTLE_DELAY_S,
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


def _normalize_city_state_args(city: str, state: str) -> tuple[str, str]:
    if city and not state:
        match = re.match(r"^\s*([^,]+?),\s*([A-Za-z]{2}|[A-Za-z][A-Za-z .'-]+)\s*$", city)
        if match:
            city = match.group(1).strip()
            state = match.group(2).strip()
    return city, state.upper() if len(state) == 2 else state


def _spoken_place(city: str, state: str) -> str:
    if city and state:
        expanded_state = _STATE_NAMES.get(state.upper(), state)
        return f"{city}, {expanded_state}"
    if city:
        return city
    if state:
        return _STATE_NAMES.get(state.upper(), state)
    return "the area"


def _tts_friendly_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    replacements = {
        "&": " and ",
        "/": " ",
        "@": " at ",
        " llc": " L L C",
        " inc": " Incorporated",
        " co.": " Company",
        " co ": " company ",
        " hwy ": " highway ",
        " rd ": " road ",
        " st ": " street ",
        " ave ": " avenue ",
        " blvd ": " boulevard ",
    }
    lowered = f" {cleaned} "
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    lowered = re.sub(r"\bETA\b", "estimated arrival", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bI-(\d+)\b", r"Interstate \1", lowered)
    lowered = re.sub(r"\bUS-(\d+)\b", r"U S \1", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip(" .,")


def _format_spoken_recommendation_summary(summary: str, city: str, state: str) -> str:
    place = _spoken_place(city, state)
    if summary:
        return _tts_friendly_text(summary)
    return f"I found some recommended mechanics near {place}."


def _format_shop_lookup_summary(summary: str, requested_shop: str, city: str, state: str) -> str:
    if summary:
        return _tts_friendly_text(summary)
    return f"I found nearby matches for {_tts_friendly_text(requested_shop)} near {_spoken_place(city, state)}."


def _format_shop_for_voice(shop: dict[str, Any]) -> str:
    name = _tts_friendly_text(str(shop.get("company_name") or "a nearby shop"))
    address = _tts_friendly_text(str(shop.get("address") or "")).strip()
    city = str(shop.get("city") or "").strip()
    state = str(shop.get("state") or "").strip()
    rating = shop.get("rating")
    distance = shop.get("distance_miles")
    reason = _tts_friendly_text(str(shop.get("reason") or "")).strip()

    location_bits = [bit for bit in [address, _spoken_place(city, state) if city or state else ""] if bit]
    details: list[str] = []
    if location_bits:
        details.append("at " + ", ".join(location_bits))
    if isinstance(distance, (int, float)):
        details.append(f"about {distance:.1f} miles away")
    if isinstance(rating, (int, float)):
        details.append(f"rated {rating:.1f} out of five")
    if reason:
        details.append(reason)

    sentence = name
    if details:
        sentence += " is " + ", ".join(details)
    return sentence.strip() + "."


def _format_mechanic_for_voice(mechanic: dict[str, Any]) -> str:
    name = _tts_friendly_text(str(mechanic.get("company_name") or "a nearby mechanic"))
    distance = mechanic.get("distance_miles")
    eta = mechanic.get("estimated_response_minutes")
    rating = mechanic.get("rating")
    reasons = [_tts_friendly_text(str(reason)) for reason in (mechanic.get("reasons") or []) if str(reason).strip()]
    location_bits = [mechanic.get("city"), _STATE_NAMES.get(str(mechanic.get("state") or "").upper(), str(mechanic.get("state") or ""))]
    location_text = ", ".join(bit for bit in location_bits if bit)

    details: list[str] = []
    if isinstance(distance, (int, float)):
        details.append(f"about {distance:.1f} miles away")
    elif location_text:
        details.append(f"based in {location_text}")
    if isinstance(eta, int) and eta > 0:
        details.append(f"with an estimated arrival around {eta} minutes")
    if isinstance(rating, (int, float)):
        details.append(f"rated {rating:.1f} out of five")

    sentence = name
    if details:
        sentence += " is " + ", ".join(details)
    if reasons:
        sentence += ". " + "; ".join(reasons[:2])
    return sentence.strip() + "."


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
            num_idle_processes=int(os.getenv("AGENT_NUM_IDLE_PROCESSES", "4")),
        )
    )