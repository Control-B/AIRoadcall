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


# Forward ref
DispatchStatusView.model_rebuild()
