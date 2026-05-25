import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

os.environ.setdefault("RETELL_BACKEND_WEBHOOK_TOKEN", "test-token")

from app.api.deps import get_session  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.models.dispatch_session import DispatchSession, DispatchSessionStatus  # noqa: E402
from app.schemas.dispatch_session import DispatchCreateSessionResponse  # noqa: E402
from app.schemas.roadside_match import (  # noqa: E402
    RoadsideCallerContext,
    RoadsideMatchResponse,
    RoadsideMechanicMatch,
)
from app.services.dispatch_session_service import DispatchSessionService  # noqa: E402
from app.services.geocoding_service import GeocodingService  # noqa: E402
from app.services.roadside_matching_service import RoadsideMatchingService  # noqa: E402


@pytest.fixture(autouse=True)
def configure_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.LIVEKIT_URL = "wss://roadcall-vob5sadf.livekit.cloud"
    settings.LIVEKIT_API_KEY = "test-key"
    settings.LIVEKIT_API_SECRET = "test-secret"
    settings.LIVEKIT_AGENT_NAME = "roadcall-agent"
    settings.ADMIN_API_KEY = "admin-test-key"
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


async def _empty_session():
    yield None


@pytest.mark.asyncio
async def test_livekit_roadside_session_returns_room_token(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()

    async def fake_reverse_geocode(lat, lng):
        return {
            "address": "Main Street and 1st Avenue",
            "city": "St. Petersburg",
            "state": "FL",
        }

    async def fake_create_session(db, payload):
        assert payload.source == "livekit_map_gps"
        assert payload.latitude == 27.77
        assert payload.longitude == -82.64
        assert payload.location_source == "browser_gps"
        return DispatchCreateSessionResponse(
            dispatch_session_id=session_id,
            public_code="RC-1234",
            status="matching",
            location_url="https://roadcall.ai/go?t=token",
            location_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=payload.city,
            state=payload.state,
            address=payload.address,
        )

    monkeypatch.setattr(GeocodingService, "reverse_geocode", fake_reverse_geocode)
    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/livekit/roadside-session",
            json={"latitude": 27.77, "longitude": -82.64, "accuracy_meters": 14},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["room_name"] == f"roadcall-{session_id}"
    assert body["livekit_url"] == "wss://roadcall-vob5sadf.livekit.cloud"
    assert body["location"]["city"] == "St. Petersburg"

    claims = jwt.decode(
        body["participant_token"],
        "test-secret",
        algorithms=["HS256"],
        issuer="test-key",
    )
    assert claims["sub"] == f"caller-{session_id}"
    assert claims["video"]["roomJoin"] is True
    assert claims["video"]["room"] == f"roadcall-{session_id}"


@pytest.mark.asyncio
async def test_livekit_roadside_session_requires_livekit_config(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    settings = get_settings()
    settings.LIVEKIT_API_SECRET = ""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/livekit/roadside-session",
            json={"latitude": 27.77, "longitude": -82.64},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "LiveKit is not configured for this environment."


@pytest.mark.asyncio
async def test_livekit_context_loads_session_for_agent(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()
    session = DispatchSession(
        public_code="RC-7788",
        source="livekit_map_gps",
        status=DispatchSessionStatus.matching.value,
        city="St. Petersburg",
        state="FL",
        address="Main Street and 1st Avenue",
        lat=27.77,
        lng=-82.64,
        location_accuracy_m=14,
        location_source="browser_gps",
        vehicle_type="box truck",
        problem_type="flat tire",
    )
    session.id = session_id
    session.caller_phone_last4 = "1212"

    async def fake_get_session(db, requested_id):
        assert requested_id == session_id
        return session

    monkeypatch.setattr(DispatchSessionService, "get_session", fake_get_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.get(f"/api/livekit/roadside-session/{session_id}/context")
        allowed = await client.get(
            f"/api/livekit/roadside-session/{session_id}/context",
            headers={"X-Admin-Key": "admin-test-key"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200, allowed.text
    body = allowed.json()
    assert body["location"]["latitude"] == 27.77
    assert body["location"]["city"] == "St. Petersburg"
    assert body["caller_phone_last4"] == "1212"
    assert body["missing_fields"] == []


@pytest.mark.asyncio
async def test_livekit_match_uses_confirmed_gps_session(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()
    session = DispatchSession(
        public_code="RC-8899",
        source="livekit_map_gps",
        status=DispatchSessionStatus.matching.value,
        city="St. Petersburg",
        state="FL",
        address="Main Street and 1st Avenue",
        lat=27.77,
        lng=-82.64,
        location_accuracy_m=14,
        location_source="browser_gps",
    )
    session.id = session_id
    recorded = {}

    async def fake_get_session(db, requested_id):
        assert requested_id == session_id
        return session

    async def fake_match_mechanic(db, request):
        assert request.latitude == 27.77
        assert request.longitude == -82.64
        assert request.vehicleType == "box truck"
        assert request.problemType == "flat tire"
        return RoadsideMatchResponse(
            status="matched",
            searchLevel="local",
            matches=[
                RoadsideMechanicMatch(
                    mechanicId=str(uuid.uuid4()),
                    businessName="Roadcall Test Repair",
                    phone="+18135551212",
                    city="St. Petersburg",
                    state="FL",
                    services=["tires"],
                    vehicleTypes=["truck"],
                    mobileService=True,
                    emergencyService=True,
                    serviceRadiusMiles=50,
                    priorityScore=90,
                    distanceMiles=4.2,
                    score=94.0,
                    reason="Nearest suitable provider",
                )
            ],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=RoadsideCallerContext(
                city="St. Petersburg",
                state="FL",
                latitude=27.77,
                longitude=-82.64,
                problemType="flat tire",
                vehicleType="box truck",
            ),
            message="Matched Roadcall Test Repair.",
        )

    async def fake_record_event(db, sid, event_type, actor_type, payload, **kwargs):
        recorded["event_type"] = event_type
        recorded["payload"] = payload

    monkeypatch.setattr(DispatchSessionService, "get_session", fake_get_session)
    monkeypatch.setattr(RoadsideMatchingService, "match_mechanic", fake_match_mechanic)
    monkeypatch.setattr(DispatchSessionService, "record_event", fake_record_event)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/livekit/roadside-session/{session_id}/match",
            headers={"X-Admin-Key": "admin-test-key"},
            json={"vehicle_type": "box truck", "problem_type": "flat tire", "limit": 1},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "matched"
    assert body["matches"][0]["businessName"] == "Roadcall Test Repair"
    assert recorded["event_type"] == "livekit.match.completed"
    assert recorded["payload"]["match_count"] == 1