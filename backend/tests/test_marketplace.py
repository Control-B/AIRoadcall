"""Tests for the public marketplace endpoints (submit / review / claim / edit).

These exercise the ownership-gate logic the user requested:
- claim auto-approves on phone match,
- claim auto-approves on subscriber Organization match,
- otherwise queues for admin review,
- only the verified owner can edit a claimed listing.
"""
import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.dialects.postgresql import ARRAY as PGARRAY, UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@compiles(PGUUID, "sqlite")
def _sqlite_uuid(element, compiler, **kw):  # pragma: no cover
    return "CHAR(36)"


@compiles(PGARRAY, "sqlite")
def _sqlite_array(element, compiler, **kw):  # pragma: no cover
    return "JSON"


from app.main import app  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.api.deps import get_session  # noqa: E402
from app.models.mechanic import Mechanic  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models import mechanic_marketplace  # noqa: E402,F401
from app.services.mechanic_data_service import MechanicDataService  # noqa: E402


@pytest_asyncio.fixture
async def db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_session] = _override

    async with TestSession() as session:
        yield session

    app.dependency_overrides.pop(get_session, None)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _make_mechanic(db, **overrides) -> Mechanic:
    m = Mechanic(
        company_name=overrides.get("company_name", "Acme Tow"),
        contact_name="Bob",
        phone=overrides.get("phone", "5555550100"),
        city="Orlando",
        state="FL",
        base_lat=28.5, base_lng=-81.4,
        service_types=overrides.get("service_types", ["tow_needed"]),
        vehicle_types_supported=overrides.get("vehicle_types_supported", ["car", "truck"]),
        accepts_mobile_roadside=overrides.get("accepts_mobile_roadside", True),
        emergency_service=overrides.get("emergency_service", True),
        service_radius_miles=overrides.get("service_radius_miles", 50),
        priority_score=overrides.get("priority_score", 50),
        rating=overrides.get("rating"),
        review_count=overrides.get("review_count"),
        source_confidence=overrides.get("source_confidence"),
        active=True,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


@pytest.mark.asyncio
async def test_submit_listing_creates_pending_review(db, client):
    payload = {
        "company_name": "Sunshine Roadside",
        "contact_name": "Maria",
        "phone": "4075551111",
        "city": "Orlando", "state": "FL",
        "service_types": ["tow_needed"],
        "vehicle_types_supported": ["truck"],
    }
    res = await client.post("/api/marketplace/submit", json=payload)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "created"
    assert body["requires_admin_review"] is True


@pytest.mark.asyncio
async def test_submit_listing_dedupes_existing_phone(db, client):
    await _make_mechanic(db, phone="4075552222")
    res = await client.post("/api/marketplace/submit", json={
        "company_name": "Dup Co", "contact_name": "X", "phone": "4075552222",
    })
    assert res.status_code == 201
    assert res.json()["status"] == "duplicate"


@pytest.mark.asyncio
async def test_review_aggregates_rating(db, client):
    m = await _make_mechanic(db)
    r1 = await client.post(f"/api/marketplace/{m.id}/review", json={"rating": 5, "reviewer_phone": "9999990001"})
    assert r1.status_code == 201, r1.text
    r2 = await client.post(f"/api/marketplace/{m.id}/review", json={"rating": 3, "reviewer_phone": "9999990002"})
    assert r2.status_code == 201
    assert r2.json()["new_review_count"] == 2
    assert abs(r2.json()["new_average"] - 4.0) < 0.01


@pytest.mark.asyncio
async def test_review_rate_limited_per_phone(db, client):
    m = await _make_mechanic(db)
    await client.post(f"/api/marketplace/{m.id}/review", json={"rating": 5, "reviewer_phone": "9999991234"})
    res = await client.post(f"/api/marketplace/{m.id}/review", json={"rating": 1, "reviewer_phone": "9999991234"})
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_claim_auto_approves_on_phone_match(db, client):
    m = await _make_mechanic(db, phone="4075553333")
    res = await client.post(f"/api/marketplace/{m.id}/claim", json={
        "claimant_name": "Owner", "claimant_phone": "(407) 555-3333",
        "subscription_product": "ai_telephony",
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["method"] == "phone_match"
    assert body["status"] == "approved"
    assert body["can_edit_now"] is True


@pytest.mark.asyncio
async def test_claim_auto_approves_on_subscriber_match(db, client):
    m = await _make_mechanic(db, phone="4075554444")
    from app.models.organization import VerticalType
    org = Organization(
        name="Subscriber Org", slug="subscriber-org",
        contact_phone="4075559999",
        vertical_type=VerticalType.shops, is_active=True,
    )
    db.add(org)
    await db.commit()
    res = await client.post(f"/api/marketplace/{m.id}/claim", json={
        "claimant_name": "Owner", "claimant_phone": "4075559999",
        "subscription_product": "ai_voice_text",
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["method"] == "subscriber_match"
    assert body["can_edit_now"] is True


@pytest.mark.asyncio
async def test_claim_falls_back_to_pending_review(db, client):
    m = await _make_mechanic(db, phone="4075555555")
    res = await client.post(f"/api/marketplace/{m.id}/claim", json={
        "claimant_name": "Stranger", "claimant_phone": "8005550000",
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["method"] == "pending_review"
    assert body["status"] == "pending"
    assert body["can_edit_now"] is False


@pytest.mark.asyncio
async def test_edit_requires_verified_ownership(db, client):
    m = await _make_mechanic(db, phone="4075556666")
    # Without a claim — must fail.
    res = await client.patch(f"/api/marketplace/{m.id}", json={
        "claimant_phone": "4075556666", "company_name": "Hacked",
    })
    assert res.status_code == 403

    # Claim first.
    await client.post(f"/api/marketplace/{m.id}/claim", json={
        "claimant_name": "Owner", "claimant_phone": "4075556666",
        "subscription_product": "ai_telephony",
    })

    # Wrong phone — must fail.
    bad = await client.patch(f"/api/marketplace/{m.id}", json={
        "claimant_phone": "8005550000", "company_name": "Hacked",
    })
    assert bad.status_code == 403

    # Right phone — should succeed.
    ok = await client.patch(f"/api/marketplace/{m.id}", json={
        "claimant_phone": "4075556666", "company_name": "New Name",
    })
    assert ok.status_code == 200, ok.text
    assert ok.json()["company_name"] == "New Name"


@pytest.mark.asyncio
async def test_claim_rejects_invalid_product(db, client):
    m = await _make_mechanic(db, phone="4075557777")
    res = await client.post(f"/api/marketplace/{m.id}/claim", json={
        "claimant_name": "Owner", "claimant_phone": "4075557777",
        "subscription_product": "pizza_delivery",  # not in allowed set
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_public_directory_search_ranks_by_inferred_roadside_intent(db):
    strong = await _make_mechanic(
        db,
        company_name="Orlando Mobile Semi Tire Repair",
        phone="4075558888",
        service_types=["flat_tire", "mobile_repair"],
        vehicle_types_supported=["heavy_duty", "truck", "semi"],
        accepts_mobile_roadside=True,
        emergency_service=True,
        rating=4.9,
        review_count=80,
        source_confidence=0.95,
    )
    await _make_mechanic(
        db,
        company_name="Orlando Light Duty Tow",
        phone="4075559998",
        service_types=["tow_needed"],
        vehicle_types_supported=["car"],
        accepts_mobile_roadside=False,
        emergency_service=False,
        rating=3.2,
        review_count=3,
        source_confidence=0.4,
    )

    result = await MechanicDataService.public_directory_search(
        db,
        q="mobile tire repair for semi truck",
        city="Orlando",
        state="FL",
        page_size=5,
    )

    assert result["search_intelligence"]["issue_type"] == "flat_tire"
    assert result["search_intelligence"]["vehicle_type"] == "heavy_duty"
    assert result["mechanics"][0]["id"] == str(strong.id)
    assert result["mechanics"][0]["dispatch_fit_score"] > 0.5
