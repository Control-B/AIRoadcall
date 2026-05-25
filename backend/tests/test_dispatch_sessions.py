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
    DispatchCreateSessionRequest,
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
async def test_retell_envelope_extracts_alternate_caller_phone_field(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    called = {}

    async def fake_create_session(db, payload):
        called["payload"] = payload
        return DispatchCreateSessionResponse(
            dispatch_session_id=uuid.uuid4(),
            public_code="RC-2233",
            status="matching",
            location_url="https://roadcall.ai/go?t=token",
            location_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/dispatch/create-session",
            headers={"Authorization": "Bearer test-token"},
            json={
                "name": "create_dispatch_session",
                "args": {"source": "retell", "caller_name": "Sam"},
                "call": {"from": "+18135551212", "callId": "call_alt_123"},
            },
        )

    assert response.status_code == 200, response.text
    assert called["payload"].caller_phone == "+18135551212"
    assert called["payload"].retell_call_id == "call_alt_123"


@pytest.mark.asyncio
async def test_retell_session_reuses_recent_map_session_when_phone_join_missing(monkeypatch):
    map_session_id = uuid.uuid4()
    map_session = DispatchSession(
        public_code="RC-9090",
        source="map_phone_button",
        status=DispatchSessionStatus.matching.value,
    )
    map_session.id = map_session_id
    map_session.lat = 27.8156
    map_session.lng = -82.7023
    map_session.address = "Park Street North and 48th Avenue, St. Petersburg, FL"
    map_session.city = "St. Petersburg"
    map_session.state = "FL"
    map_session.location_captured_at = datetime.now(timezone.utc)
    map_session.created_at = datetime.now(timezone.utc)

    class FakeDb:
        def add(self, value):
            pass

        async def flush(self):
            pass

    class TokenRow:
        id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    events = []

    async def fake_find_existing(db, payload):
        empty_retell_session = DispatchSession(public_code="RC-0001", source="retell", status=DispatchSessionStatus.awaiting_location.value)
        empty_retell_session.id = uuid.uuid4()
        empty_retell_session.retell_call_id = payload.retell_call_id
        return empty_retell_session

    async def fake_find_recent_map(db):
        return map_session

    async def fake_issue_token(db, session, expires_minutes):
        return TokenRow(), "signed-token"

    async def fake_record_event(db, session_id, event_type, actor_type, payload, **kwargs):
        events.append((session_id, event_type, payload))

    async def fake_mirror_session(session, ttl_seconds=None):
        return None

    monkeypatch.setattr(DispatchSessionService, "_find_existing_session", fake_find_existing)
    monkeypatch.setattr(DispatchSessionService, "_find_recent_map_shared_session", fake_find_recent_map)
    monkeypatch.setattr(DispatchSessionService, "_issue_location_token", fake_issue_token)
    monkeypatch.setattr(DispatchSessionService, "record_event", fake_record_event)
    from app.services.session_cache_service import SessionCacheService
    monkeypatch.setattr(SessionCacheService, "mirror_session", fake_mirror_session)

    response = await DispatchSessionService.create_session(
        FakeDb(),
        DispatchCreateSessionRequest(
            source="retell",
            retell_call_id="call_missing_phone",
            caller_name="Sam",
            expires_minutes=30,
        ),
    )

    assert response.dispatch_session_id == map_session_id
    assert map_session.retell_call_id == "call_missing_phone"
    assert map_session.lat == 27.8156
    assert map_session.address.startswith("Park Street North")
    assert any(payload.get("map_fallback_attached") is True for _, event_type, payload in events if event_type == "session.reused")


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


@pytest.mark.asyncio
async def test_session_status_runs_match_when_shared_gps_and_intake_ready(monkeypatch):
    session = DispatchSession(public_code="RC-1234", status=DispatchSessionStatus.matching.value)
    session.id = uuid.uuid4()
    session.lat = 28.0395
    session.lng = -81.9498
    session.city = "Lakeland"
    session.state = "FL"
    session.problem_type = "flat_tire"
    session.vehicle_type = "semi"
    session.payment_status = "not_required"
    session.location_captured_at = datetime.now(timezone.utc)

    calls = {}

    async def fake_latest_match(db, session_id):
        return None

    async def fake_run_match(db, matched_session):
        calls["request"] = DispatchSessionService._match_request(matched_session)
        return RoadsideMatchResponse(
            status="matched",
            searchLevel="radius_25_miles",
            matches=[],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=RoadsideCallerContext(city="Lakeland", state="FL"),
            message="matched",
        )

    monkeypatch.setattr(DispatchSessionService, "_latest_match", fake_latest_match)
    monkeypatch.setattr(DispatchSessionService, "_run_match_if_ready", fake_run_match)

    response = await DispatchSessionService.status_response(None, session)

    assert calls["request"].latitude == 28.0395
    assert calls["request"].longitude == -81.9498
    assert response.location_captured is True
    assert response.status == DispatchSessionStatus.matched.value


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


def test_status_say_confirms_shared_location_before_problem_intake(monkeypatch):
    session = DispatchSession(public_code="RC-1234", status=DispatchSessionStatus.matching.value)
    session.id = uuid.uuid4()
    session.lat = 27.8156
    session.lng = -82.7023
    session.address = "Park Street North and 48th Avenue, St. Petersburg, FL"
    session.city = "St. Petersburg"
    session.state = "FL"
    session.location_captured_at = datetime.now(timezone.utc)

    say = DispatchSessionService._say(session, None, ["problemType", "vehicleType"])

    assert "I see your shared location near Park Street North" in say
    assert say.endswith("Is that correct?")


@pytest.mark.asyncio
async def test_caller_share_creates_durable_dispatch_session(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()
    captured = {}

    async def fake_reverse_geocode(latitude, longitude):
        return {
            "city": "St. Petersburg",
            "state": "FL",
            "address": "Park Street North and 48th Avenue",
            "place_name": "Park Street North and 48th Avenue, St. Petersburg, FL",
        }

    async def fake_create_session(db, payload):
        captured["payload"] = payload
        return DispatchCreateSessionResponse(
            dispatch_session_id=session_id,
            public_code="RC-8888",
            status="matching",
            location_url="https://roadcall.ai/go?t=token",
            location_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    async def fake_store(**kwargs):
        captured["store"] = kwargs
        return {**kwargs, "ttl_seconds": 1800}

    from app.services.geocoding_service import GeocodingService
    from app.services.shared_caller_location_service import SharedCallerLocationService

    monkeypatch.setattr(GeocodingService, "reverse_geocode", fake_reverse_geocode)
    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)
    monkeypatch.setattr(SharedCallerLocationService, "store", fake_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/caller/share-location",
            json={
                "phone": "813-555-1212",
                "latitude": 27.8156,
                "longitude": -82.7023,
                "accuracy": 14,
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["dispatch_session_id"] == str(session_id)
    assert body["readable_address"] == "Park Street North and 48th Avenue, St. Petersburg, FL"
    assert captured["payload"].source == "map_phone_button"
    assert captured["payload"].latitude == 27.8156
    assert captured["payload"].address == "Park Street North and 48th Avenue, St. Petersburg, FL"
    assert captured["store"]["session_id"] == str(session_id)


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