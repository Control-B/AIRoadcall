from pydantic import BaseModel, Field
from typing import Any, Literal


class DispatchMatchByLocationRequest(BaseModel):
    location_text: str = Field(..., min_length=2, max_length=500)
    service_needed: str = Field(default="roadside assistance", max_length=200)
    vehicle_type: str | None = Field(default=None, max_length=120)
    urgency: Literal["roadside", "standard", "emergency"] = "roadside"
    limit: int = Field(default=10, ge=1, le=25)


class DispatchCoordinates(BaseModel):
    latitude: float
    longitude: float


class DispatchProviderMatch(BaseModel):
    id: str
    business_name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    latitude: float
    longitude: float
    services: list[str] = Field(default_factory=list)
    heavy_duty_support: bool = False
    roadside_support: bool = False
    mobile_mechanic: bool = False
    towing: bool = False
    availability_status: str = "unknown"
    rating: float | None = None
    response_score: float = 0.0
    distance_miles: float
    straight_line_distance: float
    drive_distance_miles: float | None = None
    estimated_drive_minutes: int | None = None
    rank_score: float
    score_reasons: list[str] = Field(default_factory=list)


class DispatchMapRoute(BaseModel):
    provider_id: str
    from_latitude: float
    from_longitude: float
    to_latitude: float
    to_longitude: float
    drive_distance_miles: float | None = None
    estimated_drive_minutes: int | None = None
    geometry: dict[str, Any] | None = None


class DispatchMatchByLocationResponse(BaseModel):
    status: Literal["matched", "no_provider_found", "geocoding_failed"]
    normalized_location: str | None = None
    coordinates: DispatchCoordinates | None = None
    confidence: float | None = None
    search_radius_miles: int | None = None
    providers: list[DispatchProviderMatch] = Field(default_factory=list)
    map_routes: list[DispatchMapRoute] = Field(default_factory=list)
    message: str
    follow_up_question: str | None = None
    mapbox_metadata: dict[str, Any] | None = None
