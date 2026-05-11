"""Verify the global middleware unwraps Retell's {name, args, call} envelope."""
import os
import json
import pytest
from httpx import AsyncClient, ASGITransport

# Must set BEFORE importing the app so settings pick it up
os.environ["RETELL_BACKEND_WEBHOOK_TOKEN"] = "test-token"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.main import app  # noqa: E402
from app.core.config import get_settings  # noqa: E402

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
