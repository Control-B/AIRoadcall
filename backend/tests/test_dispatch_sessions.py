import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("RETELL_BACKEND_WEBHOOK_TOKEN", "test-token")

from app.api.deps import get_session  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.dispatch_session import (  # noqa: E402
    DispatchCreateSessionResponse,
    DispatchSessionStatusResponse,
)
from app.schemas.roadside_match import (  # noqa: E402
    RoadsideCallerContext,
    RoadsideMatchResponse,
    RoadsideMechanicMatch,
)
from app.models.dispatch_session import DispatchSession, DispatchSessionStatus  # noqa: E402
from app.services.dispatch_session_service import DispatchSessionService  # noqa: E402


@pytest.fixture(autouse=True)
def configure_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.RETELL_BACKEND_WEBHOOK_TOKEN = "test-token"
    settings.APP_BASE_URL = "https://roadcall.ai"
    yield
    app.dependency_overrides.clear()
    from app.api.routes.go import _DISPATCH_CACHE
    _DISPATCH_CACHE.clear()


async def _empty_session():
    yield None


@pytest.mark.asyncio
async def test_create_dispatch_session_requires_retell_or_admin_auth(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    called = {}

    async def fake_create_session(db, payload):
        called["payload"] = payload
        return DispatchCreateSessionResponse(
            dispatch_session_id=uuid.uuid4(),
            public_code="RC-12345",
            status="awaiting_location",
            location_url="https://roadcall.ai/go?t=token",
            location_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post("/api/dispatch/create-session", json={"source": "retell"})
        allowed = await client.post(
            "/api/dispatch/create-session",
            headers={"Authorization": "Bearer test-token"},
            json={
                "source": "retell",
                "retell_call_id": "call_123",
                "caller_phone": "+18135551212",
                "problem_description": "flat tire",
            },
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["public_code"] == "RC-12345"
    assert called["payload"].retell_call_id == "call_123"
    assert called["payload"].caller_phone == "+18135551212"


@pytest.mark.asyncio
async def test_update_location_rejects_invalid_signed_token():
    app.dependency_overrides[get_session] = _empty_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/dispatch/update-location",
            json={
                "token": "not-a-valid-token",
                "latitude": 28.0395,
                "longitude": -81.9498,
                "accuracy_m": 15,
            },
        )

    assert response.status_code == 401
    assert "Invalid or expired location token" in response.text


@pytest.mark.asyncio
async def test_session_status_returns_ai_safe_summary(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()
    fake_session = object()

    async def fake_get_session(db, dispatch_session_id):
        assert dispatch_session_id == session_id
        return fake_session

    async def fake_status_response(db, session):
        assert session is fake_session
        return DispatchSessionStatusResponse(
            dispatch_session_id=session_id,
            public_code="RC-54321",
            status="matched",
            location_captured=True,
            city="Lakeland",
            state="FL",
            latitude=28.0395,
            longitude=-81.9498,
            problem_type="flat_tire",
            vehicle_type="semi",
            payment_status="not_required",
            match_status="matched",
            best_match={
                "company_name": "Verified Truck Repair",
                "phone_available": True,
                "distance_miles": 4.2,
            },
            say="I found Verified Truck Repair near Lakeland, FL. I’m confirming availability now.",
        )

    monkeypatch.setattr(DispatchSessionService, "get_session", fake_get_session)
    monkeypatch.setattr(DispatchSessionService, "status_response", fake_status_response)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/dispatch/session-status/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["best_match"]["company_name"] == "Verified Truck Repair"
    assert "phone" not in body["best_match"]
    assert body["say"].startswith("I found Verified Truck Repair")


def test_pre_shared_location_marks_dispatch_session_ready_for_matching():
    session = DispatchSession(public_code="RC-1234", status=DispatchSessionStatus.awaiting_location.value)

    DispatchSessionService._apply_shared_location(
        session,
        {
            "phone": "+18135551212",
            "latitude": 28.0395,
            "longitude": -81.9498,
            "accuracy": 12,
            "city": "Lakeland",
            "state": "FL",
            "address": "I-4, Lakeland, FL",
            "captured_at": "2026-05-25T02:00:00+00:00",
        },
    )

    assert session.lat == 28.0395
    assert session.lng == -81.9498
    assert session.location_accuracy_m == 12
    assert session.city == "Lakeland"
    assert session.state == "FL"
    assert session.location_source == "map_phone_button"
    assert session.location_captured_at is not None
    assert session.status == DispatchSessionStatus.matching.value
    assert session.metadata_json["pre_shared_location"] is True


@pytest.mark.asyncio
async def test_go_dispatch_persists_durable_session(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    persisted = {}

    async def fake_reverse_geocode(latitude, longitude):
        return {"city": "Lakeland", "state": "FL", "address": "I-4", "place_name": "I-4, Lakeland, FL"}

    async def fake_match(db, request):
        return RoadsideMatchResponse(
            status="matched",
            searchLevel="radius_25_miles",
            matches=[
                RoadsideMechanicMatch(
                    mechanicId=str(uuid.uuid4()),
                    businessName="Lakeland Roadside",
                    phone="+18135550000",
                    city="Lakeland",
                    state="FL",
                    services=["tire repair"],
                    vehicleTypes=["semi"],
                    mobileService=True,
                    emergencyService=True,
                    serviceRadiusMiles=50,
                    priorityScore=90,
                    distanceMiles=3.5,
                    score=98,
                    reason="Closest mobile tire provider",
                )
            ],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=RoadsideCallerContext(city="Lakeland", state="FL"),
            message="matched",
        )

    async def fake_persist_go_dispatch(db, **kwargs):
        persisted.update(kwargs)
        return object()

    from app.services.geocoding_service import GeocodingService
    from app.services.roadside_matching_service import RoadsideMatchingService

    monkeypatch.setattr(GeocodingService, "reverse_geocode", fake_reverse_geocode)
    monkeypatch.setattr(RoadsideMatchingService, "match_mechanic", fake_match)
    monkeypatch.setattr(DispatchSessionService, "persist_go_dispatch", fake_persist_go_dispatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/go/dispatch",
            json={
                "phone": "813-555-1212",
                "latitude": 28.0395,
                "longitude": -81.9498,
                "accuracy_m": 12,
                "problem": "flat tire",
                "vehicle_type": "semi",
                "name": "Sam",
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["work_order_id"] == "8135551212"
    assert body["location"]["city"] == "Lakeland"
    assert persisted["caller_phone"] == "+18135551212"
    assert persisted["caller_name"] == "Sam"
    assert persisted["location_source"] == "browser_gps"
    assert persisted["match_response"].status == "matched"