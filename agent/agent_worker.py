"""LiveKit AI Agent Worker for Roadside Assistance.

LiveKit Cloud is ALL-IN-ONE: LLM, voice/TTS/STT, phone numbers, and SIP
trunking are all managed via the LiveKit dashboard. A single LiveKit API key
handles everything — NO separate OpenAI key is needed.

This agent worker connects to LiveKit Cloud and handles two room types:

1. INBOUND (driver_intake):
   - Driver calls in via SIP trunk (phone number from LiveKit dashboard)
   - Agent collects: name, vehicle type, issue description
   - Stores structured data in participant metadata
   - When room finishes, the webhook handler creates the job

2. OUTBOUND (mechanic_dispatch):
   - Backend creates a room and SIP-dials a mechanic
   - Agent joins the room and speaks to the mechanic
   - Asks about availability, ETA
   - Stores the response in participant metadata
   - When room finishes, webhook handler records the result
"""
import json
import logging
import os

from dotenv import load_dotenv
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


# ─── System Prompts ─────────────────────────────────────


DRIVER_INTAKE_SYSTEM_PROMPT = """You are an AI roadside assistance operator. A driver is calling because they need help with their vehicle.

Your job is to collect the following information:
1. Their name
2. What type of vehicle they have (make, model, year if possible)
3. What the issue is (flat tire, dead battery, locked out, need a tow, etc.)
4. A brief description of the situation

Be calm, professional, and reassuring. The driver may be stressed or in an unsafe location.

Once you have all the information, confirm it back to them and let them know:
- They will receive a text message with a link
- The link will let them share their exact location and authorize a small hold on their card
- Once that's done, we'll find the nearest available mechanic

Keep the call SHORT and efficient — under 2 minutes ideally.

When you have collected all the information, call the store_driver_info function, then end the call politely."""


MECHANIC_DISPATCH_SYSTEM_PROMPT = """You are an AI dispatcher calling a mechanic on behalf of AI Roadside Support.

You are calling to check if the mechanic is available for a job. Here are the job details:
{job_summary}

Your tasks:
1. Identify yourself as calling from AI Roadside Support
2. Briefly describe the job (issue type, vehicle, general area)
3. Ask if they are available to take this job
4. If yes, ask for their estimated time of arrival (ETA) in minutes
5. Call the store_mechanic_response function with the result
6. Thank them and end the call

Be professional and concise. This should be a 30-60 second call.

If they decline, say thank you and end the call.
If they don't answer clearly, ask one more time, then end the call.
If you reach voicemail, call store_mechanic_response with response="no_answer" and end."""


# ─── Entry Point ────────────────────────────────────────


async def entrypoint(ctx: JobContext):
    """Main entry point for the agent worker.

    LiveKit calls this when a new room needs an agent.
    We check room metadata to determine which type of call this is.
    """
    await ctx.connect()

    room_metadata_raw = ctx.room.metadata or "{}"
    try:
        room_metadata = json.loads(room_metadata_raw)
    except (json.JSONDecodeError, TypeError):
        room_metadata = {}

    call_type = room_metadata.get("type", "")

    if call_type == "driver_intake":
        await handle_driver_intake(ctx, room_metadata)
    elif call_type == "mechanic_dispatch":
        await handle_mechanic_dispatch(ctx, room_metadata)
    else:
        logger.warning(f"Unknown room type: {call_type}, room: {ctx.room.name}")


# ─── Driver Intake Handler ──────────────────────────────


async def handle_driver_intake(ctx: JobContext, room_metadata: dict):
    """Handle an inbound driver call. Collect info and store structured data."""
    logger.info(f"Starting driver intake in room {ctx.room.name}")

    # Define the tool the agent uses to store collected data
    @llm.function_context.ai_callable(
        description="Store the collected driver information after gathering all details. "
        "Call this once you have the driver's name, vehicle, issue type, and summary."
    )
    async def store_driver_info(
        driver_name: str,
        vehicle_type: str,
        issue_type: str,
        issue_summary: str,
    ):
        """Store collected intake data in participant metadata for the webhook handler."""
        collected_data = {
            "driver_name": driver_name,
            "vehicle_type": vehicle_type,
            "issue_type": _normalize_issue_type(issue_type),
            "issue_summary": issue_summary,
        }

        await ctx.room.local_participant.update_metadata(
            json.dumps({"collected_data": collected_data})
        )

        logger.info(f"Stored driver intake data: {collected_data}")
        return "Information saved successfully. Let the driver know they'll receive a text message shortly."

    fn_ctx = llm.FunctionContext()
    fn_ctx._register_ai_function(store_driver_info)

    # LiveKit Cloud handles LLM + voice selection via the agent configuration
    # in the dashboard. We just provide the system prompt and tools.
    agent = Agent(
        instructions=DRIVER_INTAKE_SYSTEM_PROMPT,
        fnc_ctx=fn_ctx,
    )
    session = AgentSession()
    await session.start(agent=agent, room=ctx.room)

    logger.info(f"Driver intake agent running in room {ctx.room.name}")


# ─── Mechanic Dispatch Handler ──────────────────────────


async def handle_mechanic_dispatch(ctx: JobContext, room_metadata: dict):
    """Handle an outbound mechanic dispatch call."""
    mechanic_name = room_metadata.get("mechanic_name", "the mechanic")
    job_summary = room_metadata.get("job_summary", "a roadside assistance job")
    job_id = room_metadata.get("job_id", "")
    dispatch_attempt_id = room_metadata.get("dispatch_attempt_id", "")

    logger.info(
        f"Starting mechanic dispatch call in room {ctx.room.name} "
        f"to {mechanic_name} for job {job_id}"
    )

    system_prompt = MECHANIC_DISPATCH_SYSTEM_PROMPT.format(job_summary=job_summary)

    @llm.function_context.ai_callable(
        description="Store the mechanic's response to the dispatch request. "
        "You MUST call this before ending the call."
    )
    async def store_mechanic_response(
        response: str,
        eta_minutes: int | None = None,
        notes: str = "",
    ):
        """Record whether the mechanic accepted or declined.

        Args:
            response: One of 'accepted', 'declined', 'unavailable', 'no_answer'
            eta_minutes: Estimated time of arrival in minutes (if accepted)
            notes: Any additional notes from the mechanic
        """
        normalized = _normalize_mechanic_response(response)

        result = {
            "response": normalized,
            "eta_minutes": eta_minutes,
            "notes": notes,
        }

        await ctx.room.local_participant.update_metadata(
            json.dumps({"dispatch_result": result})
        )

        logger.info(
            f"Mechanic {mechanic_name} response: {normalized} "
            f"(ETA: {eta_minutes}min) for job {job_id}"
        )

        if normalized == "accepted":
            return f"Great, I've confirmed your acceptance. Thank you {mechanic_name}!"
        else:
            return f"Understood. Thank you for your time, {mechanic_name}."

    fn_ctx = llm.FunctionContext()
    fn_ctx._register_ai_function(store_mechanic_response)

    agent = Agent(
        instructions=system_prompt,
        fnc_ctx=fn_ctx,
    )
    session = AgentSession()
    await session.start(agent=agent, room=ctx.room)

    logger.info(f"Mechanic dispatch agent running in room {ctx.room.name}")


# ─── Helpers ────────────────────────────────────────────


def _normalize_mechanic_response(raw: str) -> str:
    """Normalize free-text mechanic responses to enum values."""
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
    """Map free-text issue descriptions to our enum values."""
    raw_lower = raw.lower()

    mappings = {
        "flat_tire": ["flat tire", "tire", "puncture", "blowout", "flat"],
        "dead_battery": ["battery", "dead battery", "won't start", "jump start", "jump"],
        "lockout": ["locked out", "lockout", "keys locked", "locked keys", "lock"],
        "fuel_delivery": ["fuel", "gas", "ran out of gas", "out of fuel", "no gas"],
        "tow_needed": ["tow", "towing", "need a tow", "can't drive", "won't move"],
        "engine_trouble": ["engine", "won't start", "stalled", "engine trouble", "misfire"],
        "overheating": ["overheat", "overheating", "hot", "coolant", "radiator", "steam"],
        "accident": ["accident", "crash", "collision", "hit"],
        "stuck_off_road": ["stuck", "off road", "ditch", "mud", "snow"],
    }

    for enum_val, keywords in mappings.items():
        if any(kw in raw_lower for kw in keywords):
            return enum_val

    return "other"


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            api_key=os.getenv("LIVEKIT_API_KEY", ""),
            api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
            ws_url=os.getenv("LIVEKIT_URL", ""),
        )
    )
