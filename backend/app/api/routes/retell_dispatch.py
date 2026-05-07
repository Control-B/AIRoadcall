"""Retell AI dispatch tool endpoints — Roadside API contract.

Implements the six canonical backend tools that Sandy (Retell agent) calls
during a roadside dispatch conversation:

  POST /api/calls/create-service-request
  POST /api/location/request
  GET  /api/dispatch/status/{service_request_id}
  POST /api/payment/request
  POST /api/dispatch/confirm
  POST /api/transfer/warm

All endpoints require: Authorization: Bearer <RETELL_BACKEND_WEBHOOK_TOKEN>

See docs/backend-integration.md for the full contract.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.enums.dispatch_status import DispatchStatus
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.models.dispatch_attempt import DispatchAttempt
from app.models.job import Job
from app.schemas.job import JobCreateRequest
from app.services.dispatch_service import DispatchService
from app.services.job_service import JobService
from app.services.payment_service import PaymentService
from app.services.sms_service import SMSService

logger = logging.getLogger("retell-dispatch")
settings = get_settings()

router = APIRouter(tags=["retell-dispatch"])


# ─── Auth ─────────────────────────────────────────────────────────────────────

def require_retell_auth(
    authorization: str | None = Header(default=None),
) -> None:
    expected = f"Bearer {settings.RETELL_BACKEND_WEBHOOK_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Retell webhook authorization",
        )


# ─── Request / Response models ────────────────────────────────────────────────

class CreateServiceRequestIn(BaseModel):
    retell_call_id: str
    direction: Literal["inbound", "outbound"] = "inbound"
    language: str = "en-US"
    driver_safe: bool = True
    driver_name: str
    callback_number: str
    company_name: str | None = None
    truck_type: str | None = None
    trailer_type: str | None = None
    loaded_status: str | None = None
    problem_type: str
    problem_description: str
    fault_codes: list[str] = Field(default_factory=list)
    caller_phone: str | None = None


class CreateServiceRequestOut(BaseModel):
    ok: bool
    service_request_id: str
    service_status: str
    priority: str
    next_action: str
    driver_message: str | None = None


_HIGH_PRIORITY = {
    "tire", "coolant_leak", "air_leak", "derate",
    "overheating", "no_start", "locked_brakes",
}


class ManualLocationDetails(BaseModel):
    interstate_or_highway: str | None = None
    mile_marker: str | None = None
    nearest_exit: str | None = None
    city: str | None = None
    state: str | None = None
    truck_stop: str | None = None
    landmark: str | None = None
    direction_of_travel: str | None = None


class RequestLocationIn(BaseModel):
    service_request_id: str
    callback_number: str
    preferred_channel: Literal["sms"] = "sms"
    sms_template_id: Literal["location_request"] = "location_request"
    manual_location_details: ManualLocationDetails | None = None


class RequestLocationOut(BaseModel):
    ok: bool
    location_status: str
    secure_location_token: str | None = None
    location_url: str | None = None
    expires_at: str | None = None
    driver_message: str | None = None


class DispatchStatusOut(BaseModel):
    ok: bool
    service_request_id: str
    service_status: str
    mechanic_name: str | None = None
    mechanic_company: str | None = None
    mechanic_phone: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    eta_minutes: int | None = None
    eta_text: str | None = None
    payment_required: bool = False
    payment_authorization_status: str | None = None
    tracking_token: str | None = None
    transfer_approved: bool = False
    driver_message: str | None = None


class RequestPaymentIn(BaseModel):
    service_request_id: str
    callback_number: str
    reason: Literal["diagnostic_fee", "service_authorization", "deposit"] = "diagnostic_fee"
    sms_template_id: Literal["payment_authorization"] = "payment_authorization"


class RequestPaymentOut(BaseModel):
    ok: bool
    payment_required: bool
    payment_request_id: str | None = None
    payment_url: str | None = None
    authorization_status: str
    amount_authorized_display: str | None = None
    driver_message: str | None = None


class ConfirmDispatchIn(BaseModel):
    service_request_id: str
    send_tracking_sms: bool = True
    sms_template_id: Literal["tracking_link"] = "tracking_link"


class ConfirmDispatchOut(BaseModel):
    ok: bool
    service_status: str
    eta_text: str | None = None
    tracking_url: str | None = None
    driver_message: str | None = None


class WarmTransferIn(BaseModel):
    service_request_id: str
    driver_requested_transfer: bool = True
    reason: Literal[
        "driver_coordination", "mechanic_needs_details", "dispatcher_escalation"
    ] = "driver_coordination"


class WarmTransferOut(BaseModel):
    ok: bool
    transfer_approved: bool
    transfer_phone: str | None = None
    whisper_text: str | None = None
    fallback_message: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_job_or_404(service_request_id: str, db: AsyncSession) -> Job:
    result = await db.execute(
        select(Job).where(Job.public_job_id == service_request_id.upper())
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found",
        )
    return job


def _job_service_status(job: Job) -> str:
    status_map = {
        JobStatus.awaiting_driver_location: "location_requested",
        JobStatus.driver_location_received: "matching",
        JobStatus.matching_mechanics: "matching",
        JobStatus.calling_mechanics: "matching",
        JobStatus.mechanic_accepted: "mechanic_confirmed",
        JobStatus.payment_pending: "payment_required",
        JobStatus.payment_authorized: "payment_authorized",
        JobStatus.dispatched: "dispatched",
        JobStatus.completed: "dispatched",
        JobStatus.cancelled: "failed",
        JobStatus.failed: "failed",
    }
    return status_map.get(job.status, "matching")


def _payment_auth_status(job: Job) -> str:
    pm_map = {
        PaymentStatus.not_started: "not_required",
        PaymentStatus.pending: "requested",
        PaymentStatus.authorized: "authorized",
        PaymentStatus.captured: "authorized",
        PaymentStatus.failed: "failed",
        PaymentStatus.cancelled: "failed",
    }
    return pm_map.get(job.payment_status, "not_required")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post(
    "/api/calls/create-service-request",
    response_model=CreateServiceRequestOut,
    dependencies=[Depends(require_retell_auth)],
)
async def create_service_request(
    payload: CreateServiceRequestIn,
    db: AsyncSession = Depends(get_session),
) -> CreateServiceRequestOut:
    """Create a dispatch record from Retell AI call intake."""
    priority = "high" if payload.problem_type in _HIGH_PRIORITY else "standard"

    vehicle = " ".join(filter(None, [payload.truck_type, payload.trailer_type])) or "vehicle"
    issue_summary = payload.problem_description
    if payload.fault_codes:
        issue_summary += f" | Fault codes: {', '.join(payload.fault_codes)}"

    req = JobCreateRequest(
        driver_name=payload.driver_name,
        driver_phone=payload.callback_number,
        vehicle_type=vehicle,
        issue_type=payload.problem_type,
        issue_summary=issue_summary,
    )
    resp = await JobService.create_job(db, req)
    await db.commit()

    logger.info(
        "create_service_request: job=%s retell_call=%s",
        resp.public_job_id,
        payload.retell_call_id,
    )

    return CreateServiceRequestOut(
        ok=True,
        service_request_id=resp.public_job_id,
        service_status="intake_created",
        priority=priority,
        next_action="request_location",
    )


@router.post(
    "/api/location/request",
    response_model=RequestLocationOut,
    dependencies=[Depends(require_retell_auth)],
)
async def request_location(
    payload: RequestLocationIn,
    db: AsyncSession = Depends(get_session),
) -> RequestLocationOut:
    """Generate a secure GPS token and SMS it to the driver, or collect manual location."""
    job = await _get_job_or_404(payload.service_request_id, db)

    # Manual location fallback
    if payload.manual_location_details is not None:
        d = payload.manual_location_details
        city = d.city or ""
        state = d.state or ""
        if city:
            job.driver_city = city
        if state:
            job.driver_state = state
        if d.interstate_or_highway:
            job.issue_summary = (
                (job.issue_summary or "")
                + f" | Location: {d.interstate_or_highway}"
                + (f" MM {d.mile_marker}" if d.mile_marker else "")
                + (f", near {d.nearest_exit}" if d.nearest_exit else "")
            )
        job.status = JobStatus.driver_location_received
        await db.commit()
        return RequestLocationOut(
            ok=True,
            location_status="manual_collected",
            driver_message="Manual location collected.",
        )

    # SMS magic link
    sms_sent = await SMSService.send_magic_link(
        payload.callback_number,
        job.magic_link_url if hasattr(job, "magic_link_url") else
        f"{settings.public_app_base_url}/support/{job.magic_link_token}",
        job.driver_name or "Driver",
    )

    if not sms_sent:
        return RequestLocationOut(
            ok=False,
            location_status="sms_failed",
            driver_message="Could not send SMS. Please collect location manually.",
        )

    logger.info("request_location: SMS sent to %s for job %s", payload.callback_number, job.public_job_id)

    return RequestLocationOut(
        ok=True,
        location_status="sms_sent",
        secure_location_token=job.magic_link_token,
        location_url=f"{settings.public_app_base_url}/support/{job.magic_link_token}",
        driver_message="Location link sent by text.",
    )


@router.get(
    "/api/dispatch/status/{service_request_id}",
    response_model=DispatchStatusOut,
    dependencies=[Depends(require_retell_auth)],
)
async def get_dispatch_status(
    service_request_id: str,
    db: AsyncSession = Depends(get_session),
) -> DispatchStatusOut:
    """Return current dispatch status, mechanic details, and ETA."""
    job = await _get_job_or_404(service_request_id, db)

    # Find the most recent accepted dispatch attempt
    attempt_result = await db.execute(
        select(DispatchAttempt)
        .where(DispatchAttempt.job_id == job.id)
        .where(DispatchAttempt.dispatch_status == DispatchStatus.accepted)
        .order_by(DispatchAttempt.created_at.desc())
        .limit(1)
    )
    accepted = attempt_result.scalar_one_or_none()

    mechanic_name: str | None = None
    mechanic_company: str | None = None
    mechanic_phone: str | None = None

    if accepted:
        from app.models.mechanic import Mechanic
        mech_result = await db.execute(
            select(Mechanic).where(Mechanic.id == accepted.mechanic_id)
        )
        mech = mech_result.scalar_one_or_none()
        if mech:
            mechanic_name = mech.contact_name
            mechanic_company = mech.company_name
            mechanic_phone = mech.phone

    service_status = _job_service_status(job)
    payment_required = job.payment_status in (
        PaymentStatus.not_started, PaymentStatus.pending
    ) and job.status in (JobStatus.payment_pending, JobStatus.payment_authorized)
    transfer_approved = job.status in (JobStatus.dispatched, JobStatus.completed)

    def _driver_msg() -> str:
        if service_status == "matching":
            return "Searching qualified providers."
        if service_status == "mechanic_confirmed":
            return "Provider matched. Awaiting payment authorization."
        if service_status == "payment_authorized":
            return "Payment authorized. Finalizing dispatch."
        if service_status == "dispatched":
            return "Dispatch confirmed."
        return "Status updated."

    return DispatchStatusOut(
        ok=True,
        service_request_id=job.public_job_id,
        service_status=service_status,
        mechanic_name=mechanic_name,
        mechanic_company=mechanic_company,
        mechanic_phone=mechanic_phone,
        payment_required=payment_required,
        payment_authorization_status=_payment_auth_status(job),
        tracking_token=job.magic_link_token if transfer_approved else None,
        transfer_approved=transfer_approved,
        driver_message=_driver_msg(),
    )


@router.post(
    "/api/payment/request",
    response_model=RequestPaymentOut,
    dependencies=[Depends(require_retell_auth)],
)
async def request_payment(
    payload: RequestPaymentIn,
    db: AsyncSession = Depends(get_session),
) -> RequestPaymentOut:
    """Create a Stripe manual-capture authorization and send a secure payment link."""
    job = await _get_job_or_404(payload.service_request_id, db)

    # If already authorized, just return current state
    if job.payment_status == PaymentStatus.authorized:
        payment_url = (
            f"{settings.public_app_base_url}/pay/{job.stripe_payment_intent_id}"
            if job.stripe_payment_intent_id else None
        )
        return RequestPaymentOut(
            ok=True,
            payment_required=True,
            payment_request_id=job.stripe_payment_intent_id,
            payment_url=payment_url,
            authorization_status="authorized",
            amount_authorized_display=f"${job.payment_hold_amount:.2f}",
            driver_message="Payment already authorized.",
        )

    try:
        result = await PaymentService.create_payment_intent(db, job)
        await db.commit()

        payment_url = f"{settings.public_app_base_url}/pay/{result.client_secret}"

        # Send payment link via SMS
        if payload.callback_number:
            body = (
                f"Hi {job.driver_name or 'Driver'}, tap to authorize roadside payment: "
                f"{payment_url} . Reply STOP to opt out."
            )
            await SMSService.send_sms(payload.callback_number, body)

        logger.info("request_payment: intent=%s job=%s", result.payment_intent_id, job.public_job_id)

        return RequestPaymentOut(
            ok=True,
            payment_required=True,
            payment_request_id=result.payment_intent_id,
            payment_url=payment_url,
            authorization_status="requested",
            amount_authorized_display=f"${result.amount_dollars:.2f}",
            driver_message="Secure authorization link sent.",
        )
    except Exception as exc:
        logger.error("request_payment error: %s", exc, exc_info=True)
        return RequestPaymentOut(
            ok=False,
            payment_required=True,
            authorization_status="failed",
            driver_message="Could not initiate payment. Please try again.",
        )


@router.post(
    "/api/dispatch/confirm",
    response_model=ConfirmDispatchOut,
    dependencies=[Depends(require_retell_auth)],
)
async def confirm_dispatch(
    payload: ConfirmDispatchIn,
    db: AsyncSession = Depends(get_session),
) -> ConfirmDispatchOut:
    """Finalize mechanic acceptance, send tracking link, confirm dispatch."""
    job = await _get_job_or_404(payload.service_request_id, db)

    if job.status not in (
        JobStatus.mechanic_accepted,
        JobStatus.payment_authorized,
        JobStatus.matching_mechanics,
        JobStatus.calling_mechanics,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot confirm dispatch from status: {job.status}",
        )

    job.status = JobStatus.dispatched
    tracking_url: str | None = None

    if payload.send_tracking_sms and job.driver_phone:
        tracking_url = f"{settings.public_app_base_url}/track/{job.magic_link_token}"
        body = (
            f"Hi {job.driver_name or 'Driver'}, your mechanic is on the way! "
            f"Track their arrival: {tracking_url} . Reply STOP to opt out."
        )
        await SMSService.send_sms(job.driver_phone, body)

    await db.commit()
    logger.info("confirm_dispatch: job=%s dispatched", job.public_job_id)

    return ConfirmDispatchOut(
        ok=True,
        service_status="dispatched",
        tracking_url=tracking_url,
        driver_message=(
            "Dispatch confirmed and tracking link sent."
            if payload.send_tracking_sms else "Dispatch confirmed."
        ),
    )


@router.post(
    "/api/transfer/warm",
    response_model=WarmTransferOut,
    dependencies=[Depends(require_retell_auth)],
)
async def initiate_warm_transfer(
    payload: WarmTransferIn,
    db: AsyncSession = Depends(get_session),
) -> WarmTransferOut:
    """Approve transfer, select target phone, and return whisper text."""
    job = await _get_job_or_404(payload.service_request_id, db)

    if job.status not in (JobStatus.dispatched, JobStatus.mechanic_accepted):
        return WarmTransferOut(
            ok=True,
            transfer_approved=False,
            fallback_message=(
                "Transfer is not approved until the mechanic is confirmed "
                "and dispatch is finalized."
            ),
        )

    # Find accepted mechanic
    attempt_result = await db.execute(
        select(DispatchAttempt)
        .where(DispatchAttempt.job_id == job.id)
        .where(DispatchAttempt.dispatch_status == DispatchStatus.accepted)
        .order_by(DispatchAttempt.created_at.desc())
        .limit(1)
    )
    accepted = attempt_result.scalar_one_or_none()

    mechanic_phone: str | None = None
    mechanic_company: str | None = None

    if accepted:
        from app.models.mechanic import Mechanic
        mech_result = await db.execute(
            select(Mechanic).where(Mechanic.id == accepted.mechanic_id)
        )
        mech = mech_result.scalar_one_or_none()
        if mech:
            mechanic_phone = mech.phone
            mechanic_company = mech.company_name

    if not mechanic_phone:
        return WarmTransferOut(
            ok=True,
            transfer_approved=False,
            fallback_message="No confirmed mechanic phone available for transfer.",
        )

    city_state = " ".join(filter(None, [job.driver_city, job.driver_state]))
    location_summary = city_state or (
        f"lat {job.driver_lat:.4f}, lng {job.driver_lng:.4f}"
        if job.driver_lat and job.driver_lng else "location on service request"
    )
    issue = f"{job.issue_type}: {job.issue_summary or ''}".rstrip(". ")

    whisper_text = (
        f"You are receiving a Roadcall.ai driver: {job.driver_name or 'driver'}, "
        f"callback {job.driver_phone}, "
        f"{job.vehicle_type or 'vehicle'}, "
        f"problem {issue}. "
        f"Location: {location_summary}. "
        f"Service request {job.public_job_id}."
    )

    logger.info("warm_transfer: job=%s → %s", job.public_job_id, mechanic_company)

    return WarmTransferOut(
        ok=True,
        transfer_approved=True,
        transfer_phone=mechanic_phone,
        whisper_text=whisper_text,
    )
