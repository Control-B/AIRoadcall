"""Verify the global middleware unwraps Retell's {name, args, call} envelope."""
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport

# Must set BEFORE importing the app so settings pick it up
os.environ["RETELL_BACKEND_WEBHOOK_TOKEN"] = "test-token"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.main import app  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.schemas.dispatch_session import DispatchCreateSessionResponse, DispatchSessionStatusResponse  # noqa: E402

# Force reload of settings cache so our env var takes effect
get_settings.cache_clear()
_settings = get_settings()
_settings.RETELL_BACKEND_WEBHOOK_TOKEN = "test-token"


@pytest.mark.asyncio
async def test_retell_envelope_is_unwrapped(monkeypatch):
    captured = {}

    async def fake_match(db, request):
        captured["request"] = request
        from app.schemas.roadside_match import (
            RoadsideMatchResponse,
            RoadsideCallerContext,
        )
        return RoadsideMatchResponse(
            status="matched",
            searchLevel="exact_city",
            matches=[],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=RoadsideCallerContext(),
            message="ok",
        )

    from app.services.roadside_matching_service import RoadsideMatchingService
    monkeypatch.setattr(RoadsideMatchingService, "match_mechanic", fake_match)

    async def _override_session():
        yield None

    from app.api.deps import get_session
    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Retell-style envelope
        resp = await ac.post(
            "/api/roadside/match-mechanic",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            content=json.dumps({
                "name": "match_mechanic",
                "args": {
                    "message": "tire blown",
                    "city": "Lakeland",
                    "state": "FL",
                    "problemType": "tire",
                },
                "call": {"call_id": "call_abc", "from_number": "+15555551212"},
            }),
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    req = captured["request"]
    assert req.city == "Lakeland"
    assert req.state == "FL"
    assert req.problemType == "tire"
    assert req.callerPhone == "+15555551212"
    assert req.callbackNumber == "+15555551212"


@pytest.mark.asyncio
async def test_flat_payload_still_works(monkeypatch):
    captured = {}

    async def fake_match(db, request):
        captured["request"] = request
        from app.schemas.roadside_match import (
            RoadsideMatchResponse,
            RoadsideCallerContext,
        )
        return RoadsideMatchResponse(
            status="matched",
            searchLevel="exact_city",
            matches=[],
            needsMoreInfo=False,
            missingFields=[],
            callerContext=RoadsideCallerContext(),
            message="ok",
        )

    from app.services.roadside_matching_service import RoadsideMatchingService
    monkeypatch.setattr(RoadsideMatchingService, "match_mechanic", fake_match)

    async def _override_session():
        yield None

    from app.api.deps import get_session
    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/roadside/match-mechanic",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            json={"message": "x", "city": "Lakeland", "state": "FL", "problemType": "tire"},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    assert captured["request"].city == "Lakeland"


@pytest.mark.asyncio
async def test_retell_envelope_creates_dispatch_session(monkeypatch):
    captured = {}
    session_id = uuid.uuid4()

    async def fake_create_session(db, payload):
        captured["payload"] = payload
        return DispatchCreateSessionResponse(
            dispatch_session_id=session_id,
            public_code="RC-77777",
            status="awaiting_location",
            location_url="https://roadcall.ai/go?t=signed-token",
            location_token="signed-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        )

    from app.services.dispatch_session_service import DispatchSessionService
    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)

    async def _override_session():
        yield None

    from app.api.deps import get_session
    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/dispatch/create-session",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            content=json.dumps({
                "name": "create_dispatch_session",
                "args": {"source": "retell", "problem_description": "flat tire", "vehicle_type": "semi"},
                "call": {"call_id": "call_session_123", "from_number": "+18135551212"},
            }),
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dispatch_session_id"] == str(session_id)
    assert body["location_url"].endswith("/go?t=signed-token")
    assert captured["payload"].retell_call_id == "call_session_123"
    assert captured["payload"].caller_phone == "+18135551212"




@pytest.mark.asyncio
async def test_retell_envelope_checks_dispatch_session_status(monkeypatch):
    session_id = uuid.uuid4()
    fake_session = object()

    async def fake_get_session(db, dispatch_session_id):
        assert dispatch_session_id == session_id
        return fake_session

    async def fake_status_response(db, session):
        assert session is fake_session
        return DispatchSessionStatusResponse(
            dispatch_session_id=session_id,
            public_code="RC-88888",
            status="matched",
            location_captured=True,
            city="Lakeland",
            state="FL",
            payment_status="not_required",
            match_status="matched",
            best_match={"company_name": "Lakeland Roadside", "phone_available": True},
            say="I found Lakeland Roadside near Lakeland, FL. I’m confirming availability now.",
        )

    from app.services.dispatch_session_service import DispatchSessionService
    monkeypatch.setattr(DispatchSessionService, "get_session", fake_get_session)
    monkeypatch.setattr(DispatchSessionService, "status_response", fake_status_response)

    async def _override_session():
        yield None

    from app.api.deps import get_session
    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/dispatch/session-status",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            content=json.dumps({
                "name": "get_dispatch_session_status",
                "args": {"dispatch_session_id": str(session_id)},
                "call": {"call_id": "call_session_123", "from_number": "+18135551212"},
            }),
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    assert resp.json()["best_match"]["company_name"] == "Lakeland Roadside"
