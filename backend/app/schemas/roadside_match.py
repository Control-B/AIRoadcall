from pydantic import BaseModel, Field
from typing import Optional


class RoadsideLocationInput(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    road: Optional[str] = None
    landmark: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class RoadsideMatchRequest(BaseModel):
    message: str = ""
    transcript: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    location: Optional[RoadsideLocationInput] = None
    vehicleType: Optional[str] = None
    problemType: Optional[str] = None
    callerPhone: Optional[str] = None
    callbackNumber: Optional[str] = None
    limit: int = Field(default=3, ge=1, le=10)


class RoadsideCallerContext(BaseModel):
    callerPhone: Optional[str] = None
    callbackNumber: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    road: Optional[str] = None
    landmark: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    problemType: Optional[str] = None
    vehicleType: Optional[str] = None
    serviceNeeded: Optional[str] = None
    isEmergencyRoadside: bool = True


class RoadsideMechanicMatch(BaseModel):
    mechanicId: str
    businessName: str
    phone: str
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    services: list[str]
    vehicleTypes: list[str]
    mobileService: bool
    emergencyService: bool
    serviceRadiusMiles: int
    priorityScore: int
    distanceMiles: Optional[float] = None
    score: float
    reason: str
    internalReasons: list[str] = Field(default_factory=list)


class RoadsideMajorVendorMatch(BaseModel):
    vendorId: str
    brandName: str
    locationName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    interstate: Optional[str] = None
    exitNumber: Optional[str] = None
    services: list[str] = Field(default_factory=list)
    heavyDuty: bool = False
    rvService: bool = False
    towing: bool = False
    tireService: bool = False
    is247: bool = False
    distanceMiles: Optional[float] = None
    priorityScore: int = 0
    reason: str = ""


class RoadsideMatchResponse(BaseModel):
    status: str = "needs_more_info"
    searchLevel: Optional[str] = None
    matches: list[RoadsideMechanicMatch]
    majorVendor: Optional[RoadsideMajorVendorMatch] = None
    dispatchConfidence: Optional[float] = None
    needsMoreInfo: bool
    missingFields: list[str]
    callerContext: RoadsideCallerContext
    callerLocation: Optional[RoadsideCallerContext] = None
    fallbackEscalation: bool = False
    fallbackCreated: bool = False
    message: str
