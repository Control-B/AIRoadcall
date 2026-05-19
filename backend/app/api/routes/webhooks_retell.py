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

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.models.job import Job
from app.schemas.job import JobCreateRequest
from app.services.job_service import JobService
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


# ─── endpoints ────────────────────────────────────────────────────────────────


@router.post("/save-driver-info")
async def save_driver_info(request: Request, db: AsyncSession = Depends(get_session)):
    """Create an active location session and return a short code for the agent to speak.

    Expected args: driver_name, vehicle_type, issue_type, situation_note
    Phone is resolved from Retell call metadata when available but is optional.
    Location is captured via roadcall.ai/go — no SMS required.
    """
    from app.services.caller_location_service import CallerLocationService

    body: dict[str, Any] = await request.json()
    args = _body_args(body)
    call_id: str = body.get("call_id") or body.get("call", {}).get("call_id") or ""
    logger.info("save_driver_info call_id=%s | body keys: %s", call_id, list(body.keys()))

    driver_name: str = (args.get("driver_name") or "").strip()
    vehicle_type: str = (
        args.get("vehicle_type")
        or f"{args.get('vehicle_year','')} {args.get('vehicle_make','')} {args.get('vehicle_model','')}".strip()
        or ""
    ).strip()
    issue_type: str = _normalize_issue(args.get("issue_type") or "other")
    situation_note: str = (args.get("situation_note") or "").strip()

    # Resolve caller phone from args or Retell call API — optional, used to tag the session
    driver_phone: str = (
        args.get("driver_phone")
        or args.get("phone_number")
        or args.get("caller_phone")
        or body.get("from_number")
        or ""
    ).strip()

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
                    logger.info("save_driver_info: resolved phone from Retell API: %s", driver_phone)
        except Exception as exc:
            logger.warning("save_driver_info: Retell call lookup failed: %s", exc)

    if not call_id:
        return _retell_result(
            "No call ID found. Please ask the caller for their city and highway so I can note the location manually."
        )

    try:
        session = await CallerLocationService.create_or_refresh_session(
            db,
            provider_call_id=call_id,
            caller_phone=driver_phone or None,
            call_provider="retell",
        )
        await db.commit()
        code = session.location_code
        url = CallerLocationService.public_location_url(code)
        logger.info("save_driver_info: session created code=%s call_id=%s", code, call_id)
        return _retell_result(
            f"Location code {code} is ready. "
            f"Tell the caller: Please open roadcall.ai/go in your browser, enter code {code}, "
            f"then tap Share My Location. Stay on the line. "
            f"Once they share it, call check_location with location_code {code}."
        )
    except Exception as exc:
        logger.error("save_driver_info error: %s", exc, exc_info=True)
        return _retell_result(
            f"I've noted your information for {driver_name}. "
            "Ask the caller for their highway, exit number, nearest truck stop, city, and state "
            "so I can locate them manually."
        )


@router.post("/check-location")
async def check_driver_location(request: Request, db: AsyncSession = Depends(get_session)):
    """Check whether the caller has opened roadcall.ai/go and shared GPS.

    Expected args: location_code (4-digit short code from save_driver_info)
    Also accepts call_id from Retell call context as a fallback lookup.
    """
    from app.services.caller_location_service import CallerLocationService

    body: dict[str, Any] = await request.json()
    args = _body_args(body)
    call_id: str = body.get("call_id") or body.get("call", {}).get("call_id") or ""

    # Accept location_code (new) or job_code/job_id (legacy — ignored now)
    location_code: str = (args.get("location_code") or "").strip().upper()

    try:
        session = None
        if location_code:
            session = await CallerLocationService.session_by_code(db, location_code)
        if session is None and call_id:
            session = await CallerLocationService.session_by_provider_call_id(db, call_id)

        if session is None:
            return _retell_result(
                "No active location session found. Please call save_driver_info first to get a location code."
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
            "The caller hasn't shared their location yet. "
            f"Remind them to open roadcall.ai/go, enter code {session.location_code}, "
            "and tap Share My Location. Try again in about 15 seconds."
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
    limit: int = int(args.get("limit") or 3)

    # Fall back to job coords if none provided
    if (lat == 0.0 and lng == 0.0) and job_id:
        try:
            result = await db.execute(select(Job).where(Job.public_job_id == job_id))
            job = result.scalar_one_or_none()
            if job and job.driver_lat is not None:
                lat = job.driver_lat
                lng = job.driver_lng
        except Exception:
            pass

    if lat == 0.0 and lng == 0.0:
        return _retell_result(
            "I need GPS coordinates to find nearby mechanics. "
            "Please call check_driver_location first."
        )

    try:
        from app.services.mechanic_data_service import MechanicDataService
        from app.schemas.mechanic import MechanicRecommendationRequest

        rec_req = MechanicRecommendationRequest(
            lat=lat,
            lng=lng,
            issue_type=issue_type,
            vehicle_type=vehicle_type or None,
            limit=limit,
            require_mobile_roadside=True,
            prefer_immediate=True,
        )
        data = await MechanicDataService.recommend_mechanics(db, rec_req)
        recommendations = data.recommendations if hasattr(data, "recommendations") else data.get("recommendations", [])
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
        return _retell_result("Could not search for mechanics right now. The job is logged and dispatch will follow up.")


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
