"""
Roadcall Fleet API routes.

Endpoints for fleet operators to manage incidents, vehicles, drivers,
location capture, vendor matching, and AI-assisted dispatch.
"""
from __future__ import annotations

import math
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.roadside_incident import RoadsideIncident, IncidentStatus
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.vendor import Vendor
from app.models.location_capture_session import LocationCaptureSession, LocationSessionStatus

router = APIRouter(prefix="/fleet", tags=["fleet"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_incident_id() -> str:
    chars = string.ascii_uppercase + string.digits
    return "INC-" + "".join(secrets.choice(chars) for _ in range(8))


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8  # miles
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IncidentCreate(BaseModel):
    caller_name: Optional[str] = None
    caller_phone: str
    issue_description: Optional[str] = None
    vehicle_description: Optional[str] = None
    organization_id: Optional[str] = None


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    breakdown_lat: Optional[float] = None
    breakdown_lng: Optional[float] = None
    breakdown_city: Optional[str] = None
    breakdown_state: Optional[str] = None
    breakdown_address: Optional[str] = None
    assigned_vendor_id: Optional[str] = None
    call_summary: Optional[str] = None


class LocationSubmit(BaseModel):
    token: str
    lat: float
    lng: float
    accuracy_meters: Optional[float] = None


class VehicleCreate(BaseModel):
    organization_id: str
    unit_number: str
    vin: Optional[str] = None
    year: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    vehicle_type: Optional[str] = None
    license_plate: Optional[str] = None
    license_state: Optional[str] = None
    notes: Optional[str] = None


class DriverCreate(BaseModel):
    organization_id: str
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    cdl_number: Optional[str] = None
    cdl_state: Optional[str] = None
    assigned_vehicle_id: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.post("/incidents", status_code=status.HTTP_201_CREATED)
async def create_incident(payload: IncidentCreate, db: AsyncSession = Depends(get_session)):
    incident = RoadsideIncident(
        public_incident_id=_generate_incident_id(),
        caller_name=payload.caller_name,
        caller_phone=payload.caller_phone,
        issue_description=payload.issue_description,
        vehicle_description=payload.vehicle_description,
        organization_id=uuid.UUID(payload.organization_id) if payload.organization_id else None,
        status=IncidentStatus.open,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return {"incident_id": str(incident.id), "public_incident_id": incident.public_incident_id}


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(RoadsideIncident).where(RoadsideIncident.public_incident_id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        try:
            result2 = await db.execute(
                select(RoadsideIncident).where(RoadsideIncident.id == uuid.UUID(incident_id))
            )
            inc = result2.scalar_one_or_none()
        except Exception:
            pass
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "id": str(inc.id),
        "public_incident_id": inc.public_incident_id,
        "status": inc.status,
        "caller_name": inc.caller_name,
        "caller_phone": inc.caller_phone,
        "issue_description": inc.issue_description,
        "breakdown_lat": inc.breakdown_lat,
        "breakdown_lng": inc.breakdown_lng,
        "breakdown_city": inc.breakdown_city,
        "breakdown_state": inc.breakdown_state,
        "breakdown_address": inc.breakdown_address,
        "assigned_vendor_id": str(inc.assigned_vendor_id) if inc.assigned_vendor_id else None,
        "call_summary": inc.call_summary,
        "created_at": inc.created_at.isoformat(),
        "updated_at": inc.updated_at.isoformat(),
    }


@router.patch("/incidents/{incident_id}")
async def update_incident(incident_id: str, payload: IncidentUpdate, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(RoadsideIncident).where(RoadsideIncident.public_incident_id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    update_data = payload.model_dump(exclude_none=True)
    if "status" in update_data:
        update_data["status"] = IncidentStatus(update_data["status"])
    if "assigned_vendor_id" in update_data:
        update_data["assigned_vendor_id"] = uuid.UUID(update_data["assigned_vendor_id"])

    for k, v in update_data.items():
        setattr(inc, k, v)
    inc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated"}


@router.get("/incidents")
async def list_incidents(
    organization_id: Optional[str] = None,
    incident_status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    q = select(RoadsideIncident)
    if organization_id:
        q = q.where(RoadsideIncident.organization_id == uuid.UUID(organization_id))
    if incident_status:
        q = q.where(RoadsideIncident.status == IncidentStatus(incident_status))
    q = q.order_by(RoadsideIncident.created_at.desc()).limit(limit)
    result = await db.execute(q)
    incidents = result.scalars().all()
    return [
        {
            "id": str(i.id),
            "public_incident_id": i.public_incident_id,
            "status": i.status,
            "caller_phone": i.caller_phone,
            "breakdown_state": i.breakdown_state,
            "created_at": i.created_at.isoformat(),
        }
        for i in incidents
    ]


# ---------------------------------------------------------------------------
# Location capture
# ---------------------------------------------------------------------------

@router.post("/location/request")
async def request_location(
    incident_id: str,
    phone: str,
    db: AsyncSession = Depends(get_session),
):
    """Send an SMS with a location-capture link to the driver."""
    result = await db.execute(
        select(RoadsideIncident).where(RoadsideIncident.public_incident_id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    token = secrets.token_urlsafe(32)
    loc_session = LocationCaptureSession(
        incident_id=inc.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        status=LocationSessionStatus.pending,
        sms_sent_to=phone,
    )
    db.add(loc_session)

    from app.core.config import get_settings
    from app.services.sms_provider import get_sms_provider
    cfg = get_settings()
    base_url = getattr(cfg, "PUBLIC_BASE_URL", "https://airoadcall-i76ba.ondigitalocean.app")
    link = f"{base_url}/locate/{token}"

    sms = get_sms_provider("fleet")
    sms_result = sms.send(to=phone, body=f"Roadcall: Share your location so we can send help → {link}")

    if sms_result.success:
        loc_session.status = LocationSessionStatus.link_sent

    await db.commit()
    return {
        "token": token,
        "link": link,
        "sms_sent": sms_result.success,
        "sms_provider": sms_result.provider,
    }


@router.post("/location/submit")
async def submit_location(payload: LocationSubmit, db: AsyncSession = Depends(get_session)):
    """Called by the browser location page when the driver shares coordinates."""
    result = await db.execute(
        select(LocationCaptureSession).where(LocationCaptureSession.token == payload.token)
    )
    loc_session = result.scalar_one_or_none()
    if not loc_session:
        raise HTTPException(status_code=404, detail="Token not found")
    if loc_session.expires_at < datetime.now(timezone.utc):
        loc_session.status = LocationSessionStatus.expired
        await db.commit()
        raise HTTPException(status_code=410, detail="Token expired")

    loc_session.lat = payload.lat
    loc_session.lng = payload.lng
    loc_session.accuracy_meters = payload.accuracy_meters
    loc_session.captured_at = datetime.now(timezone.utc)
    loc_session.status = LocationSessionStatus.captured

    if loc_session.incident_id:
        inc_result = await db.execute(
            select(RoadsideIncident).where(RoadsideIncident.id == loc_session.incident_id)
        )
        inc = inc_result.scalar_one_or_none()
        if inc:
            inc.breakdown_lat = payload.lat
            inc.breakdown_lng = payload.lng
            inc.location_captured_at = loc_session.captured_at

    await db.commit()
    return {"status": "captured"}


# ---------------------------------------------------------------------------
# Vendor matching
# ---------------------------------------------------------------------------

@router.get("/vendors/match")
async def match_vendors(
    lat: float,
    lng: float,
    state: Optional[str] = None,
    radius_miles: int = 100,
    limit: int = 10,
    db: AsyncSession = Depends(get_session),
):
    q = select(Vendor).where(Vendor.is_active == True)
    if state:
        q = q.where(Vendor.state == state.upper())
    result = await db.execute(q)
    vendors = result.scalars().all()

    scored = []
    for v in vendors:
        if v.lat is None or v.lng is None:
            continue
        dist = _haversine(lat, lng, v.lat, v.lng)
        if dist <= radius_miles:
            scored.append((dist, v))

    scored.sort(key=lambda x: x[0])
    return [
        {
            "id": str(v.id),
            "name": v.name,
            "phone": v.phone,
            "city": v.city,
            "state": v.state,
            "distance_miles": round(dist, 1),
            "operates_24_7": v.operates_24_7,
            "heavy_duty_capable": v.heavy_duty_capable,
            "average_rating": v.average_rating,
        }
        for dist, v in scored[:limit]
    ]


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------

@router.post("/vehicles", status_code=status.HTTP_201_CREATED)
async def create_vehicle(payload: VehicleCreate, db: AsyncSession = Depends(get_session)):
    v = Vehicle(
        organization_id=uuid.UUID(payload.organization_id),
        unit_number=payload.unit_number,
        vin=payload.vin,
        year=payload.year,
        make=payload.make,
        model=payload.model,
        vehicle_type=payload.vehicle_type,
        license_plate=payload.license_plate,
        license_state=payload.license_state,
        notes=payload.notes,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return {"vehicle_id": str(v.id)}


@router.get("/vehicles")
async def list_vehicles(organization_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Vehicle).where(
            Vehicle.organization_id == uuid.UUID(organization_id),
            Vehicle.is_active == True,
        )
    )
    vehicles = result.scalars().all()
    return [
        {"id": str(v.id), "unit_number": v.unit_number, "make": v.make, "model": v.model, "year": v.year}
        for v in vehicles
    ]


# ---------------------------------------------------------------------------
# Drivers
# ---------------------------------------------------------------------------

@router.post("/drivers", status_code=status.HTTP_201_CREATED)
async def create_driver(payload: DriverCreate, db: AsyncSession = Depends(get_session)):
    d = Driver(
        organization_id=uuid.UUID(payload.organization_id),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        cdl_number=payload.cdl_number,
        cdl_state=payload.cdl_state,
        assigned_vehicle_id=uuid.UUID(payload.assigned_vehicle_id) if payload.assigned_vehicle_id else None,
        notes=payload.notes,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return {"driver_id": str(d.id)}


@router.get("/drivers")
async def list_drivers(organization_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Driver).where(
            Driver.organization_id == uuid.UUID(organization_id),
            Driver.is_active == True,
        )
    )
    drivers = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "name": f"{d.first_name} {d.last_name}",
            "phone": d.phone,
            "assigned_vehicle_id": str(d.assigned_vehicle_id) if d.assigned_vehicle_id else None,
        }
        for d in drivers
    ]

