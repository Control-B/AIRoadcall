from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TrackingView(BaseModel):
    tracking_status: str
    driver_lat: Optional[float]
    driver_lng: Optional[float]
    mechanic_lat: Optional[float]
    mechanic_lng: Optional[float]
    mechanic_company: Optional[str]
    mechanic_contact: Optional[str]
    mechanic_last_updated: Optional[datetime]
    eta_minutes: Optional[int] = None
    started_at: Optional[datetime]
    job_status: str
