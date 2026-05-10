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
    emergency_service: bool = False
    service_radius_miles: int = Field(default=50, ge=1, le=500)
    priority_score: int = Field(default=50, ge=0, le=100)
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
    emergency_service: bool = False
    service_radius_miles: int = 50
    priority_score: int = 50
    rating: Optional[float]
    review_count: Optional[int] = None
    source: Optional[str] = None
    source_confidence: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None
    last_enriched_at: Optional[datetime] = None
    total_dispatches: int = 0
    successful_dispatches: int = 0
    avg_response_time_min: Optional[float] = None
    created_at: datetime


class MechanicAdminListItem(BaseModel):
    id: str
    company_name: str
    contact_name: str
    phone: str
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    service_types: list[str]
    vehicle_types_supported: list[str]
    active: bool
    accepts_mobile_roadside: bool
    emergency_service: bool = False
    service_radius_miles: int = 50
    priority_score: int = 50
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source: Optional[str] = None
    source_confidence: Optional[float] = None
    lead_status: Optional[str] = None
    last_enriched_at: Optional[datetime] = None
    created_at: datetime


class MechanicAdminListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[MechanicAdminListItem]


class MechanicAdminStats(BaseModel):
    total_mechanics: int
    active_mechanics: int
    total_with_phone: int
    total_with_email: int
    total_with_website: int
    roadside_mechanics: int
    sources: dict[str, int]
    top_states: list[dict[str, int | str]]


class MechanicSearchResult(BaseModel):
    id: str
    company_name: str
    contact_name: str
    phone: str
    city: Optional[str] = None
    state: Optional[str] = None
    rating: Optional[float] = None
    distance_miles: Optional[float] = None
    rank_score: float


class MechanicRecommendationRequest(BaseModel):
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    city: Optional[str] = None
    state: Optional[str] = None
    issue_type: str = ""
    vehicle_type: Optional[str] = None
    trailer_type: Optional[str] = None
    require_mobile_roadside: bool = True
    require_available_now: bool = False
    prefer_immediate: bool = True
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    limit: int = Field(default=3, ge=1, le=10)


class MechanicRecommendationView(BaseModel):
    id: str
    company_name: str
    contact_name: str
    phone: str
    city: Optional[str] = None
    state: Optional[str] = None
    distance_miles: Optional[float] = None
    rating: Optional[float] = None
    accepts_mobile_roadside: bool
    available_now: Optional[bool] = None
    availability_status: str
    estimated_response_minutes: Optional[int] = None
    reliability_score: float
    specialty_score: float
    availability_score: float
    recommendation_score: float
    reasons: list[str] = []


class MechanicRecommendationResponse(BaseModel):
    summary: str
    recommendations: list[MechanicRecommendationView]


class ShopLookupRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=255)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    city: Optional[str] = None
    state: Optional[str] = None
    limit: int = Field(default=3, ge=1, le=5)


class ShopLookupResult(BaseModel):
    id: str
    company_name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: str
    rating: Optional[float] = None
    distance_miles: Optional[float] = None
    reason: str


class ShopLookupResponse(BaseModel):
    summary: str
    matches: list[ShopLookupResult]


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
