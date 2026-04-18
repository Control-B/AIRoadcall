from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class JobCreateRequest(BaseModel):
    """Request from LiveKit/backend after AI call intake completes."""
    driver_name: str = Field(..., min_length=1, max_length=255)
    driver_phone: str = Field(..., min_length=5, max_length=30)
    vehicle_type: Optional[str] = None
    driver_city: Optional[str] = Field(default=None, max_length=120)
    driver_state: Optional[str] = Field(default=None, max_length=10)
    issue_type: str
    issue_summary: Optional[str] = None
    payment_hold_amount: Optional[float] = Field(None, ge=0)


class JobCreateResponse(BaseModel):
    public_job_id: str
    magic_link_token: str
    magic_link_url: str
    status: str
    created_at: datetime


class JobDriverView(BaseModel):
    """Safe driver-facing view of a job — no internal IDs exposed."""
    public_job_id: str
    driver_name: str
    vehicle_type: Optional[str]
    issue_type: str
    issue_summary: Optional[str]
    driver_city: Optional[str]
    driver_state: Optional[str]
    status: str
    payment_status: str
    payment_hold_amount: Optional[float]
    driver_lat: Optional[float]
    driver_lng: Optional[float]
    driver_location_captured_at: Optional[datetime]
    assigned_mechanic: Optional["AssignedMechanicSummary"] = None
    driver_eta_decision: Optional[str] = None
    created_at: datetime


class AssignedMechanicSummary(BaseModel):
    company_name: str
    contact_name: str
    eta_minutes: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class LocationUpdateRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class LocationUpdateResponse(BaseModel):
    success: bool = True
    status: str
    driver_lat: float
    driver_lng: float


# Rebuild to resolve forward refs
JobDriverView.model_rebuild()
