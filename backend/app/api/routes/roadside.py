import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.plan_deps import require_tenant_feature
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.plan_config import PlanFeature
from app.models.location_capture_session import LocationCaptureSession, LocationSessionStatus
from app.models.roadside_incident import IncidentStatus, RoadsideIncident
from app.models.tenant_provisioning import Tenant
from app.schemas.roadside_match import RoadsideMatchRequest, RoadsideMatchResponse
from app.services.dispatch_session_service import DispatchSessionService
from app.schemas.provisioning import RoadsideSessionView
from app.services.provisioning_service import ProvisioningService
from app.services.roadside_matching_service import RoadsideMatchingService
from app.utils.us_geo import infer_state_from_coordinates

router = APIRouter(prefix="/roadside", tags=["roadside"])
logger = get_logger(__name__)
provisioning_service = ProvisioningService()


class PremiumRoadsideIntakeIn(BaseModel):
    caller_name: str | None = None
    caller_phone: str
    issue_description: str | None = None
    vehicle_description: str | None = None
    breakdown_city: str | None = None
    breakdown_state: str | None = None
    breakdown_address: str | None = None
    breakdown_lat: float | None = None
    breakdown_lng: float | None = None
    retell_call_id: str | None = None
    call_summary: str | None = None


class GPSCaptureSessionIn(BaseModel):
    incident_id: str | None = None
    caller_phone: str | None = None
    expires_minutes: int = Field(default=30, ge=5, le=240)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DispatchStatusIn(BaseModel):
    incident_id: str | None = None
    job_id: str | None = None
    status: str
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FleetNotificationIn(BaseModel):
    incident_id: str | None = None
    message: str
    fleet_contact: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmergencyEscalationIn(BaseModel):
    incident_id: str | None = None
    reason: str
    severity: str = "high"
    metadata: dict[str, Any] = Field(default_factory=dict)


def _generate_public_incident_id() -> str:
    chars = string.ascii_uppercase + string.digits
    return "INC-" + "".join(secrets.choice(chars) for _ in range(8))


def _generate_location_token() -> str:
    return secrets.token_urlsafe(32)


def _caller_requested_location_override(request: RoadsideMatchRequest) -> bool:
    text = " ".join(part for part in [request.message, request.transcript] if part).lower()
    if not text:
        return False
    override_phrases = (
        "use city",
        "use the city",
        "search in",
        "look in",
        "find mechanic in",
        "mechanic in",
        "instead of my location",
        "not my gps",
        "use this city",
        "use that city",
    )
    return any(phrase in text for phrase in override_phrases)


async def _prefer_shared_gps_if_available(db: AsyncSession, request: RoadsideMatchRequest) -> RoadsideMatchRequest:
    if request.latitude is not None and request.longitude is not None:
        return request
    if _caller_requested_location_override(request):
        return request

    caller_phone = request.callerPhone or request.callbackNumber
    session = await DispatchSessionService.latest_by_phone(db, caller_phone) if caller_phone else None
    if not session or session.lat is None or session.lng is None:
        session = await DispatchSessionService._find_recent_map_shared_session(db)
    if not session or session.lat is None or session.lng is None:
        return request

    state = session.state or infer_state_from_coordinates(session.lat, session.lng)
    return request.model_copy(update={
        "latitude": session.lat,
        "longitude": session.lng,
        "city": session.city,
        "state": state,
        "callerPhone": request.callerPhone or session.caller_phone_encrypted,
        "callbackNumber": request.callbackNumber or session.caller_phone_encrypted,
    })


async def require_roadside_match_access(
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    admin_key = settings.ADMIN_API_KEY.strip()
    if admin_key and x_admin_key and x_admin_key.strip() == admin_key:
        return

    retell_token = settings.RETELL_BACKEND_WEBHOOK_TOKEN.strip()
    expected_bearer = f"Bearer {retell_token}"
    if retell_token and authorization and authorization.strip() == expected_bearer:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authorized to match mechanics",
    )


@router.post(
    "/match-mechanic",
    response_model=RoadsideMatchResponse,
    dependencies=[Depends(require_roadside_match_access)],
)
async def match_mechanic(
    request: RoadsideMatchRequest,
    db: AsyncSession = Depends(get_session),
):
    """Match a caller/driver to the best nearby mechanics using location + problem context.

    Retell wraps the body as {"name", "args", "call"} — the global middleware in
    app.main unwraps that envelope so this handler always sees the flat args.
    """
    try:
        request = await _prefer_shared_gps_if_available(db, request)
        return await RoadsideMatchingService.match_mechanic(db, request)
    except Exception as exc:
        logger.exception("roadside_match_api_error fallback_to_manual_dispatch error=%s", exc)
        context = RoadsideMatchingService.build_context(request)
        return RoadsideMatchResponse(
            status="manual_dispatch_required",
            searchLevel="api_error_fallback",
            matches=[],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=context,
            callerLocation=context,
            fallbackEscalation=True,
            fallbackCreated=True,
            message="I’m having trouble checking live availability, but I can still create a manual dispatch request.",
        )


@router.post(
    "/premium/intake",
    dependencies=[Depends(require_tenant_feature(PlanFeature.roadside_intake))],
)
async def premium_roadside_intake(
    payload: PremiumRoadsideIntakeIn,
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.roadside_intake)),
    db: AsyncSession = Depends(get_session),
):
    incident = RoadsideIncident(
        public_incident_id=_generate_public_incident_id(),
        organization_id=tenant.organization_id,
        caller_name=payload.caller_name,
        caller_phone=payload.caller_phone,
        issue_description=payload.issue_description,
        vehicle_description=payload.vehicle_description,
        breakdown_city=payload.breakdown_city,
        breakdown_state=payload.breakdown_state,
        breakdown_address=payload.breakdown_address,
        breakdown_lat=payload.breakdown_lat,
        breakdown_lng=payload.breakdown_lng,
        location_captured_at=datetime.now(timezone.utc) if payload.breakdown_lat and payload.breakdown_lng else None,
        retell_call_id=payload.retell_call_id,
        call_summary=payload.call_summary,
        status=IncidentStatus.open,
    )
    db.add(incident)
    await db.flush()
    session = await provisioning_service.create_roadside_session(
        db,
        tenant=tenant,
        session_type="roadside_intake",
        status="created",
        incident_id=incident.id,
        payload=payload.model_dump(exclude_none=True),
    )
    await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        incident_id=incident.id,
        event_type="roadside.intake.created",
        payload={"public_incident_id": incident.public_incident_id},
    )
    await db.commit()
    return {
        "ok": True,
        "incident_id": str(incident.id),
        "public_incident_id": incident.public_incident_id,
        "roadside_session_id": str(session.id),
        "status": incident.status,
    }


@router.post(
    "/premium/gps-capture-session",
    dependencies=[Depends(require_tenant_feature(PlanFeature.gps_capture))],
)
async def premium_gps_capture_session(
    payload: GPSCaptureSessionIn,
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.gps_capture)),
    db: AsyncSession = Depends(get_session),
):
    incident_uuid = uuid.UUID(payload.incident_id) if payload.incident_id else None
    token = _generate_location_token()
    location_session = LocationCaptureSession(
        incident_id=incident_uuid,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=payload.expires_minutes),
        status=LocationSessionStatus.pending,
        sms_sent_to=payload.caller_phone,
    )
    db.add(location_session)
    await db.flush()
    roadside_session = await provisioning_service.create_roadside_session(
        db,
        tenant=tenant,
        session_type="gps_capture",
        status="pending",
        incident_id=incident_uuid,
        payload={"location_capture_session_id": str(location_session.id), **payload.metadata},
    )
    await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        incident_id=incident_uuid,
        event_type="roadside.location.requested",
        payload={"location_capture_session_id": str(location_session.id)},
    )
    await db.commit()
    base_url = get_settings().public_app_base_url
    return {
        "ok": True,
        "roadside_session_id": str(roadside_session.id),
        "location_capture_session_id": str(location_session.id),
        "token": token,
        "location_url": f"{base_url}/locate/{token}",
        "expires_at": location_session.expires_at.isoformat(),
    }


@router.post(
    "/premium/match-mechanic",
    response_model=RoadsideMatchResponse,
    dependencies=[Depends(require_tenant_feature(PlanFeature.mechanic_assignment))],
)
async def premium_match_mechanic(
    request: RoadsideMatchRequest,
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.mechanic_assignment)),
    db: AsyncSession = Depends(get_session),
):
    response = await RoadsideMatchingService.match_mechanic(db, request)
    await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        event_type="roadside.mechanic.match_requested",
        payload={"match_count": len(response.matches), "status": response.status},
    )
    await db.commit()
    return response


@router.post(
    "/premium/dispatch-status",
    dependencies=[Depends(require_tenant_feature(PlanFeature.real_time_roadside_status))],
)
async def premium_dispatch_status(
    payload: DispatchStatusIn,
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.real_time_roadside_status)),
    db: AsyncSession = Depends(get_session),
):
    incident_uuid = uuid.UUID(payload.incident_id) if payload.incident_id else None
    job_uuid = uuid.UUID(payload.job_id) if payload.job_id else None
    if incident_uuid:
        incident = await db.get(RoadsideIncident, incident_uuid)
        if incident and payload.status in {item.value for item in IncidentStatus}:
            incident.status = IncidentStatus(payload.status)
            incident.updated_at = datetime.now(timezone.utc)
    event = await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        incident_id=incident_uuid,
        job_id=job_uuid,
        event_type="roadside.dispatch.status_updated",
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return {"ok": True, "dispatch_event_id": str(event.id), "status": payload.status}


@router.post(
    "/premium/fleet-notification",
    dependencies=[Depends(require_tenant_feature(PlanFeature.fleet_notification))],
)
async def premium_fleet_notification(
    payload: FleetNotificationIn,
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.fleet_notification)),
    db: AsyncSession = Depends(get_session),
):
    incident_uuid = uuid.UUID(payload.incident_id) if payload.incident_id else None
    event = await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        incident_id=incident_uuid,
        event_type="roadside.fleet.notification_queued",
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return {"ok": True, "dispatch_event_id": str(event.id), "status": "queued"}


@router.post(
    "/premium/emergency-escalation",
    dependencies=[Depends(require_tenant_feature(PlanFeature.emergency_routing))],
)
async def premium_emergency_escalation(
    payload: EmergencyEscalationIn,
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.emergency_routing)),
    db: AsyncSession = Depends(get_session),
):
    incident_uuid = uuid.UUID(payload.incident_id) if payload.incident_id else None
    event = await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        incident_id=incident_uuid,
        event_type="roadside.emergency.escalated",
        status="urgent",
        payload=payload.model_dump(exclude_none=True),
    )
    await db.commit()
    return {"ok": True, "dispatch_event_id": str(event.id), "status": "urgent"}


@router.post(
    "/premium/external-dispatch-api",
    dependencies=[Depends(require_tenant_feature(PlanFeature.external_dispatch_api))],
)
async def premium_external_dispatch_api(
    payload: dict[str, Any],
    tenant: Tenant = Depends(require_tenant_feature(PlanFeature.external_dispatch_api)),
    db: AsyncSession = Depends(get_session),
):
    event = await provisioning_service.record_dispatch_event(
        db,
        tenant_id=tenant.id,
        organization_id=tenant.organization_id,
        event_type="roadside.external_dispatch.received",
        payload=payload,
    )
    await db.commit()
    return {"ok": True, "dispatch_event_id": str(event.id), "status": "accepted"}
