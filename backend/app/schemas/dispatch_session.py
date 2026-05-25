from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DispatchCreateSessionRequest(BaseModel):
    source: str = "api"
    retell_call_id: str | None = None
    twilio_call_sid: str | None = None
    caller_phone: str | None = None
    caller_name: str | None = None
    problem_type: str | None = None
    problem_description: str | None = None
    vehicle_type: str | None = None
    vehicle_description: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    location_source: str | None = None
    expires_minutes: int = Field(default=15, ge=5, le=240)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DispatchCreateSessionResponse(BaseModel):
    dispatch_session_id: UUID
    public_code: str
    status: str
    location_url: str
    location_token: str
    expires_at: datetime
    location_captured: bool = False
    city: str | None = None
    state: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy_m: float | None = None
    location_source: str | None = None
    location_captured_at: datetime | None = None
    say: str | None = None


class SharedLocationContext(BaseModel):
    lat: float
    lng: float
    accuracy: float | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None


class ActiveCallContext(BaseModel):
    caller_phone: str | None = None
    session_id: UUID
    location_confirmed: bool = False
    shared_location: SharedLocationContext | None = None
    instruction: str


class ActiveCallContextRequest(BaseModel):
    source: str = "retell"
    retell_call_id: str | None = None
    caller_phone: str | None = None
    expires_minutes: int = Field(default=30, ge=5, le=240)


class ActiveCallContextResponse(BaseModel):
    ok: bool = True
    active_call_context: ActiveCallContext
    say: str


class DispatchUpdateLocationRequest(BaseModel):
    token: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy_m: float | None = None
    source: str = "browser_gps"
    city: str | None = None
    state: str | None = None
    address: str | None = None
    problem_type: str | None = None
    problem_description: str | None = None
    vehicle_type: str | None = None


class DispatchSessionStatusResponse(BaseModel):
    dispatch_session_id: UUID
    public_code: str
    status: str
    location_captured: bool
    city: str | None = None
    state: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_accuracy_m: float | None = None
    location_source: str | None = None
    location_captured_at: datetime | None = None
    problem_type: str | None = None
    vehicle_type: str | None = None
    payment_status: str
    match_status: str | None = None
    best_match: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    say: str


class DispatchSessionStatusRequest(BaseModel):
    dispatch_session_id: UUID


class DispatchUpdateLocationResponse(BaseModel):
    ok: bool = True
    session: DispatchSessionStatusResponse


class DispatchLinkCaseCodeRequest(BaseModel):
    public_code: str
    caller_phone_last4: str | None = Field(default=None, min_length=4, max_length=4)
    expires_minutes: int = Field(default=15, ge=5, le=240)


class DispatchLinkCaseCodeResponse(BaseModel):
    dispatch_session_id: UUID
    public_code: str
    location_url: str
    location_token: str
    expires_at: datetime