import pytest

from app.api.routes.roadside import _prefer_shared_gps_if_available
from app.schemas.roadside_match import RoadsideMatchRequest


@pytest.mark.asyncio
async def test_city_search_does_not_use_latest_phone_matched_gps(monkeypatch):
    request = RoadsideMatchRequest(
        message="I have a flat tire",
        city="Tampa",
        state="FL",
        callerPhone="+18135551212",
        problemType="flat_tire",
        vehicleType="semi",
    )

    resolved = await _prefer_shared_gps_if_available(None, request)

    assert resolved.latitude is None
    assert resolved.longitude is None
    assert resolved.city == "Tampa"
    assert resolved.state == "FL"


@pytest.mark.asyncio
async def test_respects_explicit_city_override(monkeypatch):
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


@pytest.mark.asyncio
async def test_does_not_use_recent_map_gps_when_caller_gives_city(monkeypatch):
    request = RoadsideMatchRequest(
        message="I have a tire problem",
        city="Dallas",
        state="TX",
        problemType="flat_tire",
        vehicleType="semi",
    )

    resolved = await _prefer_shared_gps_if_available(None, request)

    assert resolved.latitude is None
    assert resolved.longitude is None
    assert resolved.city == "Dallas"
    assert resolved.state == "TX"
    assert resolved.callerPhone is None


@pytest.mark.asyncio
async def test_keeps_explicit_lat_lng_when_tool_passes_precise_location(monkeypatch):
    request = RoadsideMatchRequest(
        message="I have a tire problem",
        city="Tampa",
        state="FL",
        latitude=27.9506,
        longitude=-82.4572,
        problemType="flat_tire",
        vehicleType="semi",
    )

    resolved = await _prefer_shared_gps_if_available(None, request)

    assert resolved.latitude == 27.9506
    assert resolved.longitude == -82.4572
    assert resolved.city == "Tampa"
