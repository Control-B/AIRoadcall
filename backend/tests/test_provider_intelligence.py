from types import SimpleNamespace

from app.services.provider_intelligence_service import ProviderIntelligenceService


def mechanic(**overrides):
    defaults = dict(
        company_name="Orlando Mobile Diesel Fleet Service",
        address="Orlando, FL",
        website="https://example.com",
        service_types=["tow_needed", "engine_trouble", "flat_tire"],
        vehicle_types_supported=["truck", "heavy_duty", "fleet"],
        accepts_mobile_roadside=True,
        emergency_service=True,
        service_radius_miles=75,
        total_dispatches=20,
        successful_dispatches=18,
        avg_response_time_min=24,
        rating=4.8,
        review_count=85,
        source_confidence=0.9,
        active=True,
        hours_of_operation=None,
        email="ops@example.com",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_provider_score_rewards_operational_fit():
    strong = ProviderIntelligenceService.score_provider(
        mechanic(),
        issue_type="tow_needed",
        vehicle_type="truck",
        distance_miles=8,
    )
    weak = ProviderIntelligenceService.score_provider(
        mechanic(
            service_types=[],
            vehicle_types_supported=[],
            accepts_mobile_roadside=False,
            emergency_service=False,
            total_dispatches=0,
            successful_dispatches=0,
            rating=3.1,
            review_count=2,
            source_confidence=0.35,
            avg_response_time_min=90,
        ),
        issue_type="tow_needed",
        vehicle_type="truck",
        distance_miles=70,
    )

    assert strong.score > weak.score
    assert strong.dispatch_fit_score > weak.dispatch_fit_score
    assert strong.trust_score > weak.trust_score
    assert "Roadside-ready" in strong.badges
    assert strong.estimated_response_minutes == 24


def test_provider_score_exposes_breakdown_and_reasons():
    score = ProviderIntelligenceService.score_provider(
        mechanic(),
        issue_type="engine_trouble",
        vehicle_type="heavy_duty",
        distance_miles=12,
    )

    assert set(score.breakdown) == {
        "distance",
        "roadside_capability",
        "service_match",
        "reliability",
        "availability",
        "review_quality",
        "response_speed",
        "fleet_fit",
    }
    assert 0 <= score.score <= 1
    assert score.trust_level in {"elite", "trusted", "qualified", "needs_verification"}
    assert any("engine trouble" in reason or "heavy duty" in reason for reason in score.reasons)


def test_mobile_required_penalizes_non_mobile_provider():
    mobile = ProviderIntelligenceService.score_provider(
        mechanic(accepts_mobile_roadside=True),
        issue_type="flat_tire",
        vehicle_type="truck",
        distance_miles=20,
        require_mobile_roadside=True,
    )
    shop_only = ProviderIntelligenceService.score_provider(
        mechanic(accepts_mobile_roadside=False),
        issue_type="flat_tire",
        vehicle_type="truck",
        distance_miles=20,
        require_mobile_roadside=True,
    )

    assert mobile.roadside_relevance_score > shop_only.roadside_relevance_score
    assert mobile.dispatch_fit_score > shop_only.dispatch_fit_score
