from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MechanicCreateRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=5, max_length=30)
    service_types: list[str] = []
    vehicle_types_supported: list[str] = []
    base_lat: float
    base_lng: float
    active: bool = True
    accepts_mobile_roadside: bool = True
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source: Optional[str] = None
    source_confidence: Optional[float] = None
    source_url: Optional[str] = None
    hours_of_operation: Optional[dict] = None
    address: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None


class MechanicLocationUpdate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class MechanicView(BaseModel):
    id: str
    company_name: str
    contact_name: str
    phone: str
    service_types: list[str]
    vehicle_types_supported: list[str]
    base_lat: float
    base_lng: float
    active: bool
    accepts_mobile_roadside: bool
    rating: Optional[float]
    review_count: Optional[int] = None
    source: Optional[str] = None
    source_confidence: Optional[float] = None
    address: Optional[str] = None
    website: Optional[str] = None
    last_enriched_at: Optional[datetime] = None
    total_dispatches: int = 0
    successful_dispatches: int = 0
    avg_response_time_min: Optional[float] = None
    created_at: datetime


# ── Pipeline Schemas ────────────────────────────────────


class ScrapeRequest(BaseModel):
    """Request to trigger an Apify scrape job."""
    location: str = Field(
        ..., description="City/area to search, e.g. 'Austin, TX'"
    )
    radius_miles: int = Field(default=25, ge=1, le=100)
    max_results: int = Field(default=50, ge=1, le=200)


class ScrapeStatusView(BaseModel):
    """Status of a running or completed scrape."""
    run_id: str
    status: str  # READY, RUNNING, SUCCEEDED, FAILED, TIMED-OUT, ABORTED
    records_found: int = 0
    records_upserted: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class EnrichRequest(BaseModel):
    """Request to enrich mechanics with Tavily data."""
    mechanic_ids: Optional[list[str]] = Field(
        default=None,
        description="Specific mechanic IDs to enrich. If null, enriches stale records."
    )
    max_age_hours: int = Field(
        default=168,
        description="Enrich mechanics not enriched in this many hours (default 7 days)"
    )
    limit: int = Field(default=20, ge=1, le=100)


class EnrichResultView(BaseModel):
    mechanic_id: str
    company_name: str
    enriched: bool
    updates: dict = {}
    error: Optional[str] = None


class PipelineStatsView(BaseModel):
    total_mechanics: int
    active_mechanics: int
    sources: dict[str, int]  # source -> count
    never_enriched: int
    stale_enrichment: int  # older than 7 days
    avg_rating: Optional[float]
    avg_source_confidence: Optional[float]
    total_dispatches: int
    successful_dispatches: int
