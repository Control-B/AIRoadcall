from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.deps import get_session
from app.api.routes import dispatch
from app.services import geocoding_service
from app.services.geocoding_service import GeocodingService
from app.services.location_matching_service import LocationMatchingService
from app.services.travel_time_service import TravelTimeResult, TravelTimeService


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, _statement):
        return _FakeResult(self.rows)


async def _override_session():
    yield _FakeDb([])


def _mechanic(name, lat, lng, city, *, services=None, vehicles=None, priority=50, rating=4.0):
    return SimpleNamespace(
        id=uuid4(),
        company_name=name,
        phone="+15550000000",
        email=None,
        address=f"{city} shop",
        city=city,
        state="FL",
        zip_code=None,
        base_lat=lat,
        base_lng=lng,
        service_types=services or ["mobile truck repair", "tire repair"],
        vehicle_types_supported=vehicles or ["heavy_duty", "semi", "trailer"],
        accepts_mobile_roadside=True,
        emergency_service=True,
        service_radius_miles=200,
        priority_score=priority,
        response_score=None,
        availability_status="unknown",
        rating=rating,
        active=True,
    )


@pytest.mark.asyncio
async def test_geocode_location_prefers_florida_city(monkeypatch):
    geocoding_service._GEOCODE_CACHE.clear()
    monkeypatch.setattr(geocoding_service.settings, "MAPBOX_ACCESS_TOKEN", "test-token")

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "features": [
                    {
                        "center": [-82.6403, 27.7676],
                        "place_name": "St. Petersburg, Florida, United States",
                        "text": "St. Petersburg",
                        "place_type": ["place"],
                        "relevance": 0.9,
                        "context": [{"id": "region.123", "short_code": "US-FL", "text": "Florida"}],
                    }
                ]
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params):
            assert params["country"] == "us"
            assert params["bbox"]
            return _Response()

    monkeypatch.setattr(geocoding_service.httpx, "AsyncClient", _Client)

    result = await GeocodingService.geocode_location("Saint Petersburg, FL")

    assert result["normalized_location"] == "St. Petersburg, Florida, United States"
    assert result["latitude"] == 27.7676
    assert result["longitude"] == -82.6403
    assert result["state"] == "FL"
    assert result["confidence"] >= 0.9


@pytest.mark.asyncio
async def test_radius_expansion_returns_nearby_before_distant(monkeypatch):
    origin_lat, origin_lng = 27.7676, -82.6403
    clearwater = _mechanic("Clearwater Diesel", 27.9659, -82.8001, "Clearwater", priority=40)
    jacksonville = _mechanic("Jacksonville Diesel", 30.3322, -81.6557, "Jacksonville", priority=100, rating=5.0)
    db = _FakeDb([clearwater, jacksonville])

    async def fake_drive_times(origin_lat, origin_lng, candidates, max_candidates=10):
        return {
            str(candidate.id): TravelTimeResult(
                provider_id=str(candidate.id),
                drive_distance_miles=candidate.straight_line_distance * 1.2,
                estimated_drive_minutes=round(candidate.straight_line_distance * 1.5),
            )
            for candidate in candidates
        }

    monkeypatch.setattr(TravelTimeService, "estimate_drive_times", fake_drive_times)

    providers, radius = await LocationMatchingService.find_nearby_providers(
        db,
        latitude=origin_lat,
        longitude=origin_lng,
        service_needed="semi truck tire repair",
        vehicle_type="semi truck",
        urgency="roadside",
        limit=5,
    )

    assert radius == 25
    assert providers[0].business_name == "Clearwater Diesel"
    assert all(provider.city != "Jacksonville" for provider in providers)


@pytest.mark.asyncio
async def test_radius_expands_to_lakeland_when_no_tampa_bay_provider(monkeypatch):
    origin_lat, origin_lng = 27.7676, -82.6403
    lakeland = _mechanic("Lakeland Mobile Diesel", 28.0395, -81.9498, "Lakeland")
    db = _FakeDb([lakeland])

    async def fake_drive_times(*args, **kwargs):
        return {}

    monkeypatch.setattr(TravelTimeService, "estimate_drive_times", fake_drive_times)

    providers, radius = await LocationMatchingService.find_nearby_providers(
        db,
        latitude=origin_lat,
        longitude=origin_lng,
        service_needed="semi truck tire repair",
        vehicle_type="semi truck",
        urgency="roadside",
        limit=5,
    )

    assert radius in {50, 75}
    assert providers[0].city == "Lakeland"


@pytest.mark.asyncio
async def test_no_provider_found_within_150_miles():
    origin_lat, origin_lng = 27.7676, -82.6403
    atlanta = _mechanic("Atlanta Diesel", 33.7490, -84.3880, "Atlanta")
    db = _FakeDb([atlanta])

    providers, radius = await LocationMatchingService.find_nearby_providers(
        db,
        latitude=origin_lat,
        longitude=origin_lng,
        service_needed="semi truck tire repair",
        vehicle_type="semi truck",
        urgency="roadside",
        limit=5,
    )

    assert providers == []
    assert radius is None


@pytest.mark.asyncio
async def test_match_by_location_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/dispatch/match-by-location",
            json={"location_text": "Saint Petersburg, FL", "service_needed": "semi truck tire repair"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_match_by_location_api_returns_backend_ranked_provider(monkeypatch):
    app.dependency_overrides[get_session] = _override_session
    monkeypatch.setattr(dispatch.get_settings(), "RETELL_BACKEND_WEBHOOK_TOKEN", "test-token")

    async def fake_geocode(location_text):
        return {
            "normalized_location": "St. Petersburg, Florida",
            "latitude": 27.7676,
            "longitude": -82.6403,
            "confidence": 0.98,
            "mapbox_metadata": {"source": "test"},
        }

    candidate = _mechanic("Clearwater Diesel", 27.9659, -82.8001, "Clearwater")

    async def fake_find(*args, **kwargs):
        provider = LocationMatchingService.__dict__["_load_candidates"]
        loaded = await provider(_FakeDb([candidate]), latitude=27.7676, longitude=-82.6403, radius_miles=25)
        loaded[0].drive_distance_miles = 22.3
        loaded[0].estimated_drive_minutes = 29
        loaded[0].rank_score = 112
        return loaded, 25

    monkeypatch.setattr(dispatch.GeocodingService, "geocode_location", fake_geocode)
    monkeypatch.setattr(dispatch.LocationMatchingService, "find_nearby_providers", fake_find)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/dispatch/match-by-location",
            headers={"Authorization": "Bearer test-token"},
            json={"location_text": "Saint Petersburg, FL", "service_needed": "semi truck tire repair", "vehicle_type": "semi truck"},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "matched"
    assert body["normalized_location"] == "St. Petersburg, Florida"
    assert body["search_radius_miles"] == 25
    assert body["providers"][0]["business_name"] == "Clearwater Diesel"
    assert body["providers"][0]["estimated_drive_minutes"] == 29
