from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TrackingView(BaseModel):
    tracking_status: str
    driver_lat: Optional[float]
    driver_lng: Optional[float]
    driver_location_captured_at: Optional[datetime] = None
    mechanic_lat: Optional[float]
    mechanic_lng: Optional[float]
    mechanic_company: Optional[str]
    mechanic_contact: Optional[str]
    mechanic_address: Optional[str] = None
    mechanic_city: Optional[str] = None
    mechanic_state: Optional[str] = None
    mechanic_last_updated: Optional[datetime]
    eta_minutes: Optional[int] = None
    distance_miles: Optional[float] = None
    started_at: Optional[datetime]
    job_status: str


class MechanicTrackingView(BaseModel):
    public_job_id: str
    job_status: str
    driver_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    issue_type: Optional[str] = None
    issue_summary: Optional[str] = None
    driver_lat: Optional[float] = None
    driver_lng: Optional[float] = None
    driver_location_captured_at: Optional[datetime] = None
    mechanic_lat: Optional[float] = None
    mechanic_lng: Optional[float] = None
    mechanic_company: Optional[str] = None
    mechanic_contact: Optional[str] = None
    eta_minutes: Optional[int] = None
    distance_miles: Optional[float] = None
