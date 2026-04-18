from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DispatchStartResponse(BaseModel):
    success: bool
    job_status: str
    message: str


class DispatchNextResponse(BaseModel):
    dispatch_attempt_id: str
    mechanic_company: str
    mechanic_contact: str
    mechanic_phone: str = ""
    rank_score: float
    dispatch_status: str


class MechanicResponseRequest(BaseModel):
    dispatch_attempt_id: str
    response: str = Field(..., description="accepted, declined, unavailable, no_answer, timed_out")
    eta_minutes: Optional[int] = None
    notes: Optional[str] = None


class MechanicResponseResponse(BaseModel):
    success: bool
    dispatch_status: str
    job_status: str
    assigned_mechanic_id: Optional[str] = None


class DispatchStatusView(BaseModel):
    job_status: str
    payment_status: str
    assigned_mechanic: Optional["AssignedMechanicDispatchView"] = None
    total_attempts: int = 0
    current_attempt_status: Optional[str] = None


class AssignedMechanicDispatchView(BaseModel):
    company_name: str
    contact_name: str
    eta_minutes: Optional[int] = None


class MechanicOfferView(BaseModel):
    """Mechanic-facing dispatch offer (from signed link)."""

    public_job_id: str
    issue_type: str
    issue_summary: Optional[str] = None
    vehicle_type: Optional[str] = None
    driver_area: Optional[str] = None
    driver_lat: Optional[float] = None
    driver_lng: Optional[float] = None
    dispatch_attempt_id: str
    dispatch_status: str
    suggested_eta_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    offer_state: str = Field(
        ...,
        description="active | superseded | filled | closed",
    )
    job_filled: bool = False


class MechanicOfferStatusView(BaseModel):
    """Lightweight poll payload for non-winning mechanics."""

    offer_state: str
    job_filled: bool
    dispatch_status: str
    public_job_id: str


class MechanicOfferRespondRequest(BaseModel):
    response: str = Field(..., description="accepted or declined")
    eta_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    notes: Optional[str] = None


class RematchCandidateView(BaseModel):
    mechanic_id: str
    company_name: str
    contact_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    rating: Optional[float] = None
    distance_miles: Optional[float] = None
    estimated_eta_minutes: Optional[int] = None
    rank_score: float
    base_lat: float
    base_lng: float


class DriverEtaDecisionRequest(BaseModel):
    decision: str = Field(..., description="accepted or rejected")


class RematchSelectRequest(BaseModel):
    mechanic_id: str = Field(..., description="UUID of chosen mechanic from rematch list")


# Forward ref
DispatchStatusView.model_rebuild()
