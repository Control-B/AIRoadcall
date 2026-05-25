import pytest

from app.api.routes.roadside import _prefer_shared_gps_if_available
from app.models.dispatch_session import DispatchSession
from app.schemas.roadside_match import RoadsideMatchRequest
from app.services.dispatch_session_service import DispatchSessionService


@pytest.mark.asyncio
async def test_uses_latest_phone_matched_gps_over_city_only_args(monkeypatch):
    session = DispatchSession(public_code="RC-1234")
    session.lat = 28.0395
    session.lng = -81.9498
    session.city = "Lakeland"
    session.state = "FL"
    session.caller_phone_encrypted = "8135551212"

    async def fake_latest_by_phone(db, caller_phone):
        assert caller_phone == "+18135551212"
        return session

    monkeypatch.setattr(DispatchSessionService, "latest_by_phone", fake_latest_by_phone)

    request = RoadsideMatchRequest(
        message="I have a flat tire",
        city="Tampa",
        state="FL",
        callerPhone="+18135551212",
        problemType="flat_tire",
        vehicleType="semi",
    )

    resolved = await _prefer_shared_gps_if_available(None, request)

    assert resolved.latitude == 28.0395
    assert resolved.longitude == -81.9498
    assert resolved.city == "Lakeland"


@pytest.mark.asyncio
async def test_respects_explicit_city_override(monkeypatch):
    async def fail_latest_by_phone(db, caller_phone):
        raise AssertionError("latest_by_phone should not be called for explicit city override")

    monkeypatch.setattr(DispatchSessionService, "latest_by_phone", fail_latest_by_phone)

    request = RoadsideMatchRequest(
        message="Use city Tampa instead of my location",
        city="Tampa",
        state="FL",
        callerPhone="+18135551212",
        problemType="flat_tire",
        vehicleType="semi",
    )

    resolved = await _prefer_shared_gps_if_available(None, request)

    assert resolved.latitude is None
    assert resolved.city == "Tampa"
