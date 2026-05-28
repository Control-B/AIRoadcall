"""Retell AI function-call webhook handlers.

When Retell's LLM calls a custom tool, it sends a POST to the configured
webhook URL with the call metadata and tool arguments. We execute the logic
here and return a plain string result that Retell reads aloud to the driver.

Endpoints:
  POST /retell/save-driver-info   — create job + send magic link SMS
  POST /retell/check-location     — poll whether driver GPS has arrived
  POST /retell/find-mechanics     — search mechanic DB by coords / city
  POST /retell/dispatch           — SMS dispatch offers to top mechanics
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.models.job import Job
from app.services.dispatch_service import DispatchService

logger = logging.getLogger("retell-webhooks")
settings = get_settings()

router = APIRouter(prefix="/retell", tags=["retell"])

# ─── helpers ──────────────────────────────────────────────────────────────────

ISSUE_TYPE_ALIASES: dict[str, str] = {
    "flat": "flat_tire",
    "flat tire": "flat_tire",
    "tow": "towing",
    "towing": "towing",
    "dead battery": "battery",
    "battery": "battery",
    "jump start": "battery",
    "jumpstart": "battery",
    "fuel": "fuel_delivery",
    "gas": "fuel_delivery",
    "out of gas": "fuel_delivery",
    "lockout": "lockout",
    "locked out": "lockout",
    "lock": "lockout",
    "accident": "accident",
    "overheating": "overheating",
    "engine": "mechanical",
    "mechanical": "mechanical",
    "other": "other",
}


def _normalize_issue(raw: str) -> str:
    return ISSUE_TYPE_ALIASES.get(raw.lower().strip(), raw.lower().strip() or "other")


def _retell_result(result_str: str) -> dict:
    """Wrap plain-text result in the shape Retell expects."""
    return {"result": result_str}


def _body_args(body: dict) -> dict:
    """Extract tool arguments from the Retell function-call payload.

    Retell sends either ``{"args": {...}}`` or flattens args at the top level.
    """
    return body.get("args", body)


def _nested_call(body: dict) -> dict:
    call = body.get("call")
    return call if isinstance(call, dict) else {}


def _extract_call_id(body: dict, args: dict) -> str:
    call = _nested_call(body)
    for source in (args, body, call):
        for key in ("retell_call_id", "call_id", "callId", "id"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _extract_caller_phone(body: dict, args: dict) -> str:
    call = _nested_call(body)
    sources = [args, body, call]
    for nested_key in ("metadata", "call_metadata", "telephony_metadata"):
        nested = call.get(nested_key)
        if isinstance(nested, dict):
            sources.append(nested)
    for source in sources:
        for key in (
            "driver_phone",
            "phone_number",
            "phoneNumber",
            "caller_phone",
            "callerPhone",
            "from_number",
            "fromNumber",
            "from",
        ):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


# ─── endpoints ────────────────────────────────────────────────────────────────


@router.post("/save-driver-info")
async def save_driver_info(request: Request, db: AsyncSession = Depends(get_session)):
    """Create an active location session, attach pre-shared GPS, and look up
    or upsert the caller profile keyed by phone.

    Expected args: driver_name, vehicle_type, issue_type, situation_note,
    truck_number?, trailer_number?, company_name?
    """
    from app.services.caller_location_service import CallerLocationService
    from app.services.caller_profile_service import CallerProfileService
    from app.services.shared_caller_location_service import SharedCallerLocationService

    body: dict[str, Any] = await request.json()
    args = _body_args(body)
    call_id = _extract_call_id(body, args)
    logger.info("save_driver_info call_id=%s | body keys: %s", call_id, list(body.keys()))

    driver_name: str = (args.get("driver_name") or "").strip()
    vehicle_description = (
        f"{args.get('vehicle_year', '')} "
        f"{args.get('vehicle_make', '')} "
        f"{args.get('vehicle_model', '')}"
    ).strip()
    vehicle_type: str = (args.get("vehicle_type") or vehicle_description or "").strip()
    truck_number: str = (args.get("truck_number") or args.get("unit_number") or "").strip()
    trailer_number: str = (args.get("trailer_number") or "").strip()
    company_name: str = (args.get("company_name") or args.get("company") or "").strip()

    # Resolve caller phone from args or Retell call API — optional, used to tag the session
    driver_phone = _extract_caller_phone(body, args)

    if not driver_phone and call_id:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"https://api.retellai.com/v2/get-call/{call_id}",
                    headers={"Authorization": f"Bearer {settings.RETELL_API_KEY}"},
                )
                if r.status_code == 200:
                    driver_phone = r.json().get("from_number", "")
                    logger.info(
                        "save_driver_info: resolved phone from Retell API: %s",
                        driver_phone,
                    )
        except Exception as exc:
            logger.warning("save_driver_info: Retell call lookup failed: %s", exc)

    if not call_id:
        return _retell_result(
            "No call ID found. Please ask the caller for their city and highway "
            "so I can note the location manually."
        )

    try:
        session = await CallerLocationService.create_or_refresh_session(
            db,
            provider_call_id=call_id,
            caller_phone=driver_phone or None,
            call_provider="retell",
        )

        # Profile lookup BEFORE upsert so we can detect returning callers.
        existing_profile = await CallerProfileService.get_by_phone(db, driver_phone)
        is_returning = existing_profile is not None

        # Upsert with whatever the agent passed this turn (also bumps call_count).
        await CallerProfileService.upsert(
            db,
            phone=driver_phone or "",
            driver_name=driver_name or None,
            vehicle_type=vehicle_type or None,
            truck_number=truck_number or None,
            trailer_number=trailer_number or None,
            company_name=company_name or None,
        )

        # Look up location the caller pre-shared from the website.
        shared = await SharedCallerLocationService.consume(driver_phone) if driver_phone else None
        location_line = ""
        if shared and shared.get("latitude") is not None and shared.get("longitude") is not None:
            session.latitude = shared["latitude"]
            session.longitude = shared["longitude"]
            session.accuracy = shared.get("accuracy")
            session.address = shared.get("address") or session.address
            session.city = shared.get("city") or session.city
            session.state = shared.get("state") or session.state
            session.status = "location_received"
            where = (
                f"near {session.city}, {session.state}"
                if session.city and session.state
                else f"at {session.latitude:.4f}, {session.longitude:.4f}"
            )
            location_line = f"I already have your GPS from the website {where}. "
            logger.info(
                "save_driver_info: hydrated location from website share phone=%s call_id=%s",
                driver_phone, call_id,
            )
        else:
            logger.info(
                "save_driver_info: no pre-shared location for phone=%s call_id=%s",
                driver_phone,
                call_id,
            )

        await db.commit()

        # Build the spoken response.
        if is_returning and existing_profile is not None:
            summary = CallerProfileService.summarize(existing_profile)
            confirm = (
                f"Welcome back. I have you on file as {summary}. " if summary else "Welcome back. "
            )
            confirm += (
                "Is anything different today — company, truck number, trailer number, or vehicle? "
                "If something changed, tell me and I will update it with update_caller_profile."
            )
            if location_line:
                return _retell_result(
                    location_line + confirm + " Then we'll find the closest help."
                )
            return _retell_result(
                confirm
                + " Also, please share the highway, exit, nearest truck stop, city, and state."
            )

        # First-time caller path
        if location_line:
            return _retell_result(
                location_line + "Now call find_nearby_mechanics to match the closest help."
            )
        return _retell_result(
            f"Thanks {driver_name or 'driver'}. I don't see a shared location for this number yet. "
            "Please tell me the highway, exit number, nearest truck stop, city, and state — "
            "or tap 'Share my location' on roadcall.ai and call back."
        )
    except Exception as exc:
        logger.error("save_driver_info error: %s", exc, exc_info=True)
        return _retell_result(
            f"I've noted your information for {driver_name}. "
            "Ask the caller for their highway, exit number, nearest truck stop, city, and state "
            "so I can locate them manually."
        )


@router.post("/update-caller-profile")
async def update_caller_profile(request: Request, db: AsyncSession = Depends(get_session)):
    """Update the caller's stored profile mid-call when something changed.

    Expected args (any subset): driver_name, vehicle_type, truck_number,
    trailer_number, company_name. Phone is taken from the Retell call envelope.
    """
    from app.services.caller_profile_service import CallerProfileService

    body: dict[str, Any] = await request.json()
    args = _body_args(body)
    driver_phone = _extract_caller_phone(body, args)
    if not driver_phone:
        return _retell_result("I can't update the profile without a phone number on this call.")

    fields = {
        "driver_name": (args.get("driver_name") or "").strip() or None,
        "vehicle_type": (args.get("vehicle_type") or "").strip() or None,
        "truck_number": (args.get("truck_number") or args.get("unit_number") or "").strip() or None,
        "trailer_number": (args.get("trailer_number") or "").strip() or None,
        "company_name": (args.get("company_name") or args.get("company") or "").strip() or None,
    }
    if not any(fields.values()):
        return _retell_result("Nothing to update — no new values were given.")

    profile = await CallerProfileService.upsert(
        db, phone=driver_phone, bump_call_count=False, **fields
    )
    await db.commit()
    changed = ", ".join(k.replace("_", " ") for k, v in fields.items() if v)
    summary = CallerProfileService.summarize(profile) if profile else ""
    logger.info("update_caller_profile: phone=%s changed=%s", driver_phone, changed)
    if summary:
        return _retell_result(f"Updated {changed}. I now have you as {summary}.")
    return _retell_result(f"Updated {changed}.")


@router.post("/check-location")
async def check_driver_location(request: Request, db: AsyncSession = Depends(get_session)):
    """Re-check whether the caller has shared their location.

    First tries the website pre-share cache (by inbound caller phone), then
    falls back to the active call session record.
    Expected args: call_id from Retell call context (auto-injected).
    """
    from app.services.caller_location_service import CallerLocationService
    from app.services.shared_caller_location_service import SharedCallerLocationService

    body: dict[str, Any] = await request.json()
    args = _body_args(body)
    call_id = _extract_call_id(body, args)
    caller_phone = _extract_caller_phone(body, args)

    try:
        session = None
        if call_id:
            try:
                session = await CallerLocationService.session_by_provider_call_id(db, call_id)
            except LookupError:
                session = None

        # Caller may have shared location AFTER we created the session — re-check Redis.
        if (
            session is not None
            and session.latitude is None
            and (caller_phone or session.caller_phone)
        ):
            shared = await SharedCallerLocationService.consume(caller_phone or session.caller_phone)
            if shared and shared.get("latitude") is not None:
                session.latitude = shared["latitude"]
                session.longitude = shared["longitude"]
                session.accuracy = shared.get("accuracy")
                session.address = shared.get("address") or session.address
                session.city = shared.get("city") or session.city
                session.state = shared.get("state") or session.state
                session.status = "location_received"
                await db.commit()

        if session is None and caller_phone:
            shared = await SharedCallerLocationService.lookup(caller_phone)
            if (
                shared
                and shared.get("latitude") is not None
                and shared.get("longitude") is not None
            ):
                lat, lng = float(shared["latitude"]), float(shared["longitude"])
                city = shared.get("city") or ""
                state = shared.get("state") or ""
                loc = f"near {city}, {state}" if city and state else f"at {lat:.4f}, {lng:.4f}"
                return _retell_result(
                    f"GPS confirmed {loc}. "
                    f"Coordinates: latitude {lat}, longitude {lng}. "
                    "You can now call find_nearby_mechanics."
                )

        if session is None:
            return _retell_result(
                "No active call session. Please call save_driver_info first."
            )

        if session.latitude is not None and session.longitude is not None:
            lat, lng = session.latitude, session.longitude
            city = session.city or ""
            state = session.state or ""
            loc = f"near {city}, {state}" if city and state else f"at {lat:.4f}, {lng:.4f}"
            return _retell_result(
                f"GPS confirmed {loc}. "
                f"Coordinates: latitude {lat}, longitude {lng}. "
                "You can now call find_nearby_mechanics."
            )

        if session.manual_location_text:
            return _retell_result(
                f"Manual location confirmed: {session.manual_location_text}. "
                "You can now call find_nearby_mechanics."
            )

        return _retell_result(
            "I still don't have a location for this caller. "
            "Ask for highway, exit number, nearest truck stop, city, and state — "
            "or have them tap 'Share my location' on roadcall.ai."
        )
    except Exception as exc:
        logger.error("check_location error: %s", exc, exc_info=True)
        return _retell_result("Could not check location right now. Please try again in a moment.")


@router.post("/find-mechanics")
async def find_nearby_mechanics(request: Request, db: AsyncSession = Depends(get_session)):
    """Search the mechanic database for matches near the driver.

    Expected args: job_id, latitude, longitude, issue_type, vehicle_type
    """
    body: dict[str, Any] = await request.json()
    args = _body_args(body)

    # Sandy's tool sends 'job_code'; also accept legacy 'job_id'
    job_id: str = (args.get("job_code") or args.get("job_id") or "").strip().upper()
    try:
        lat = float(args.get("latitude") or args.get("lat") or 0)
        lng = float(args.get("longitude") or args.get("lng") or 0)
    except (TypeError, ValueError):
        lat, lng = 0.0, 0.0
    issue_type: str = _normalize_issue(args.get("issue_type") or "other")
    vehicle_type: str = (args.get("vehicle_type") or "").strip()
    city: str = (args.get("city") or args.get("driver_city") or "").strip()
    state: str = (args.get("state") or args.get("driver_state") or "").strip()
    call_id = _extract_call_id(body, args)
    caller_phone = _extract_caller_phone(body, args)
    limit: int = int(args.get("limit") or 3)

    # Fall back to job/session/shared-location coords if none provided.
    if (lat == 0.0 and lng == 0.0) and job_id:
        try:
            result = await db.execute(select(Job).where(Job.public_job_id == job_id))
            job = result.scalar_one_or_none()
            if job and job.driver_lat is not None:
                lat = job.driver_lat
                lng = job.driver_lng
                city = city or job.driver_city or ""
                state = state or job.driver_state or ""
        except Exception:
            pass

    if lat == 0.0 and lng == 0.0 and call_id:
        try:
            from app.services.caller_location_service import CallerLocationService

            session = await CallerLocationService.session_by_provider_call_id(db, call_id)
            if session.latitude is not None and session.longitude is not None:
                lat = session.latitude
                lng = session.longitude
                city = city or session.city or ""
                state = state or session.state or ""
        except Exception:
            pass

    if lat == 0.0 and lng == 0.0 and caller_phone:
        try:
            from app.services.shared_caller_location_service import SharedCallerLocationService

            shared = await SharedCallerLocationService.lookup(caller_phone)
            if (
                shared
                and shared.get("latitude") is not None
                and shared.get("longitude") is not None
            ):
                lat = float(shared["latitude"])
                lng = float(shared["longitude"])
                city = city or shared.get("city") or ""
                state = state or shared.get("state") or ""
        except Exception:
            pass

    if lat == 0.0 and lng == 0.0 and not (city and state):
        return _retell_result(
            "I need a location before I can search the mechanic database. "
            "Please call check_location first or use the caller's city and state."
        )

    try:
        from app.schemas.mechanic import MechanicRecommendationRequest
        from app.services.mechanic_data_service import MechanicDataService

        rec_req = MechanicRecommendationRequest(
            lat=lat if lat != 0.0 else None,
            lng=lng if lng != 0.0 else None,
            city=city or None,
            state=state or None,
            issue_type=issue_type,
            vehicle_type=vehicle_type or None,
            limit=limit,
            require_mobile_roadside=True,
            prefer_immediate=True,
        )
        data = await MechanicDataService.recommend_mechanics(db, rec_req)
        recommendations = (
            data.recommendations
            if hasattr(data, "recommendations")
            else data.get("recommendations", [])
        )
        if not recommendations:
            return _retell_result(
                "No available mechanics found nearby right now. "
                "The job is logged and our dispatch team will follow up shortly."
            )

        lines = [f"Found {len(recommendations)} mechanics near your location:"]
        for m in recommendations[:limit]:
            if hasattr(m, "company_name"):
                name = m.company_name or m.contact_name or "a mechanic"
                dist = getattr(m, "distance_miles", None)
            else:
                name = m.get("company_name") or m.get("contact_name") or "a mechanic"
                dist = m.get("distance_miles")
            dist_str = f" ({dist:.1f} mi away)" if dist else ""
            lines.append(f"- {name}{dist_str}")

        return _retell_result(" ".join(lines) + ". I'll dispatch them now.")
    except Exception as exc:
        logger.error("find_mechanics error: %s", exc, exc_info=True)
        return _retell_result(
            "Could not search for mechanics right now. "
            "The job is logged and dispatch will follow up."
        )


@router.post("/dispatch")
async def dispatch_to_mechanics(request: Request, db: AsyncSession = Depends(get_session)):
    """SMS dispatch offers to top-ranked nearby mechanics.

    Expected args: job_id, count (optional, default 3)
    """
    body: dict[str, Any] = await request.json()
    args = _body_args(body)

    # Sandy's tool sends 'job_code'; also accept legacy 'job_id'
    job_id: str = (args.get("job_code") or args.get("job_id") or "").strip().upper()
    count: int = int(args.get("count") or 3)

    if not job_id:
        return _retell_result("No job code provided. Please save driver info first.")

    try:
        result = await db.execute(select(Job).where(Job.public_job_id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            return _retell_result(f"Job {job_id} not found.")

        # Advance job status if needed
        from app.enums.job_status import JobStatus
        if job.status not in (JobStatus.matching_mechanics, JobStatus.calling_mechanics):
            job.status = JobStatus.matching_mechanics
            await db.flush()

        batch = await DispatchService.dispatch_mechanics_batch(db, job.id, count)
        await db.commit()

        dispatched = len(batch) if batch else 0

        if dispatched == 0:
            return _retell_result(
                f"No mechanics could be dispatched for job {job_id} right now. "
                "The job is logged and dispatch will keep trying."
            )

        names = [item.mechanic_company or "a mechanic" for item in batch[:3]]
        names_str = ", ".join(names)
        return _retell_result(
            f"Done — texted {dispatched} nearby mechanics for job {job_id}: {names_str}. "
            "Each received the job details with accept and decline links. "
            "When a mechanic accepts, the driver will see their name, ETA, and live location "
            "on the link I texted them."
        )
    except Exception as exc:
        logger.error("dispatch error: %s", exc, exc_info=True)
        return _retell_result(
            f"Could not dispatch mechanics for job {job_id} right now. "
            "The job is logged and our team will follow up."
        )
