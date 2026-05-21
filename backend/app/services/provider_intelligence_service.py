"""Deterministic provider intelligence and marketplace scoring.

This is Layer 1 of the Roadcall.ai intelligence architecture: cheap,
predictable SQL/filter/weight based ranking for dispatch and marketplace search.
No LLM is required for basic provider selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.models.mechanic import Mechanic
from app.services.mechanic_data_service import MechanicDataService


DEFAULT_DISPATCH_WEIGHTS: dict[str, float] = {
    "distance": 0.22,
    "roadside_capability": 0.18,
    "service_match": 0.16,
    "reliability": 0.14,
    "availability": 0.12,
    "review_quality": 0.08,
    "response_speed": 0.06,
    "fleet_fit": 0.04,
}

SERVICE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "flat_tire": ("tire", "flat", "wheel", "rim"),
    "dead_battery": ("battery", "jump", "jumpstart", "electrical"),
    "fuel_delivery": ("fuel", "gas", "diesel", "def"),
    "tow_needed": ("tow", "towing", "wrecker", "recovery", "winch"),
    "engine_trouble": ("engine", "diesel", "mechanic", "repair", "diagnostic"),
    "trailer_repair": ("trailer", "reefer", "brake", "air leak", "mudflap"),
    "lockout": ("lock", "lockout", "keys"),
    "rv": ("rv", "camper", "motorhome"),
    "heavy_duty": ("semi", "heavy", "diesel", "truck", "fleet"),
}


@dataclass(frozen=True)
class ProviderScore:
    score: float
    dispatch_fit_score: float
    trust_score: float
    roadside_relevance_score: float
    response_confidence_score: float
    quality_score: float
    estimated_response_minutes: int | None
    availability_status: str
    trust_level: str
    reasons: list[str]
    badges: list[str]
    breakdown: dict[str, float]


@dataclass(frozen=True)
class ProviderSearchIntent:
    query: str
    issue_type: str
    vehicle_type: str | None
    service_terms: list[str]
    location_terms: list[str]
    capability_terms: list[str]
    highway_terms: list[str]


class ProviderIntelligenceService:
    """Weighted deterministic scoring used by marketplace + dispatch UX."""

    _QUERY_STOP_WORDS = {
        "a", "an", "and", "around", "at", "best", "by", "closest", "find", "for",
        "in", "me", "near", "nearby", "need", "of", "on", "open", "please", "service",
        "services", "shop", "shops", "the", "to", "with",
    }

    _SERVICE_ALIASES: dict[str, tuple[str, ...]] = {
        "flat_tire": ("flat", "tire", "tyre", "wheel", "rim", "puncture"),
        "dead_battery": ("battery", "jump", "jumpstart", "electrical", "alternator"),
        "fuel_delivery": ("fuel", "diesel", "def", "gas"),
        "tow_needed": ("tow", "towing", "wrecker", "recovery", "winch", "haul"),
        "engine_trouble": ("engine", "diesel", "diagnostic", "diagnostics", "mechanic", "repair", "freightliner", "cummins", "paccar", "detroit"),
        "trailer_repair": ("trailer", "reefer", "brake", "brakes", "welding", "weld", "air", "mudflap", "landing", "door"),
        "lockout": ("lock", "lockout", "keys"),
        "heavy_duty": ("semi", "heavy", "heavy-duty", "truck", "fleet", "tractor", "class8", "class", "freightliner", "kenworth", "peterbilt"),
    }

    _VEHICLE_ALIASES: dict[str, tuple[str, ...]] = {
        "heavy_duty": ("semi", "heavy", "heavy-duty", "tractor", "class8", "freightliner", "kenworth", "peterbilt"),
        "truck": ("truck", "diesel"),
        "trailer": ("trailer", "reefer"),
        "fleet": ("fleet", "fleets"),
    }

    @staticmethod
    def infer_search_intent(query: str | None = None, explicit_service_type: str | None = None) -> ProviderSearchIntent:
        """Infer dispatch/search intent from a public natural-language query.

        This is deterministic and embeddings-ready: it exposes normalized issue,
        vehicle, capability, and highway tokens that can later seed semantic
        search without changing the API contract.
        """
        raw_query = (query or "").strip()
        normalized_service = (explicit_service_type or "").strip().lower().replace(" ", "_").replace("-", "_")
        words = re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", raw_query.lower().replace("24/7", "24_7"))
        highway_terms = re.findall(r"\b(?:i|ih|interstate|us|hwy|highway)[-\s]?\d{1,3}\b", raw_query.lower())
        searchable_words = [word for word in words if word not in ProviderIntelligenceService._QUERY_STOP_WORDS]

        issue_type = normalized_service
        service_terms: list[str] = []
        if not issue_type:
            for service, aliases in ProviderIntelligenceService._SERVICE_ALIASES.items():
                matches = [word for word in searchable_words if word in aliases]
                if matches:
                    issue_type = service
                    service_terms.extend(matches)
                    break
        else:
            service_terms.append(issue_type)

        vehicle_type = None
        for vehicle, aliases in ProviderIntelligenceService._VEHICLE_ALIASES.items():
            if any(word in aliases for word in searchable_words):
                vehicle_type = vehicle
                break

        capability_terms = sorted({
            word for word in searchable_words
            if any(word in aliases for aliases in ProviderIntelligenceService._SERVICE_ALIASES.values())
            or any(word in aliases for aliases in ProviderIntelligenceService._VEHICLE_ALIASES.values())
        })
        location_terms = [word for word in searchable_words if word not in capability_terms and not word.isdigit()]

        return ProviderSearchIntent(
            query=raw_query,
            issue_type=issue_type,
            vehicle_type=vehicle_type,
            service_terms=service_terms,
            location_terms=location_terms,
            capability_terms=capability_terms,
            highway_terms=highway_terms,
        )

    @staticmethod
    def score_provider(
        mechanic: Mechanic | Any,
        *,
        issue_type: str = "",
        vehicle_type: str | None = None,
        distance_miles: float | None = None,
        require_mobile_roadside: bool = True,
        weights: dict[str, float] | None = None,
    ) -> ProviderScore:
        weights = weights or DEFAULT_DISPATCH_WEIGHTS
        service_score, service_reasons = ProviderIntelligenceService._service_match_score(
            mechanic,
            issue_type=issue_type,
            vehicle_type=vehicle_type,
        )
        roadside_score = ProviderIntelligenceService._roadside_relevance_score(mechanic, require_mobile_roadside)
        reliability_score = ProviderIntelligenceService._reliability_score(mechanic)
        availability_score, availability_status = ProviderIntelligenceService._availability_score(mechanic)
        quality_score = ProviderIntelligenceService._review_quality_score(mechanic)
        estimated_response_minutes = MechanicDataService._estimated_response_minutes(mechanic, distance_miles)
        response_speed_score = MechanicDataService._response_speed_score(estimated_response_minutes)
        distance_score = ProviderIntelligenceService._distance_score(distance_miles, mechanic)
        fleet_score = ProviderIntelligenceService._fleet_fit_score(mechanic)

        weighted = {
            "distance": distance_score * weights["distance"],
            "roadside_capability": roadside_score * weights["roadside_capability"],
            "service_match": service_score * weights["service_match"],
            "reliability": reliability_score * weights["reliability"],
            "availability": availability_score * weights["availability"],
            "review_quality": quality_score * weights["review_quality"],
            "response_speed": response_speed_score * weights["response_speed"],
            "fleet_fit": fleet_score * weights["fleet_fit"],
        }
        raw_score = sum(weighted.values()) / max(sum(weights.values()), 1.0)
        dispatch_fit = round(min(max(raw_score, 0.0), 1.0), 4)
        trust_score = round((quality_score * 0.42) + (reliability_score * 0.38) + (roadside_score * 0.20), 4)
        response_confidence = round((response_speed_score * 0.45) + (availability_score * 0.35) + (reliability_score * 0.20), 4)
        marketplace_score = round((dispatch_fit * 0.70) + (trust_score * 0.20) + (response_confidence * 0.10), 4)

        reasons = ProviderIntelligenceService._build_reasons(
            mechanic,
            service_reasons=service_reasons,
            distance_miles=distance_miles,
            estimated_response_minutes=estimated_response_minutes,
            trust_score=trust_score,
            availability_status=availability_status,
        )
        badges = ProviderIntelligenceService._build_badges(
            mechanic,
            trust_score=trust_score,
            response_confidence_score=response_confidence,
            roadside_score=roadside_score,
        )

        return ProviderScore(
            score=marketplace_score,
            dispatch_fit_score=dispatch_fit,
            trust_score=trust_score,
            roadside_relevance_score=round(roadside_score, 4),
            response_confidence_score=response_confidence,
            quality_score=round(quality_score, 4),
            estimated_response_minutes=estimated_response_minutes,
            availability_status=availability_status,
            trust_level=ProviderIntelligenceService._trust_level(trust_score),
            reasons=reasons,
            badges=badges,
            breakdown={key: round(value, 4) for key, value in weighted.items()},
        )

    @staticmethod
    def _service_match_score(mechanic: Mechanic | Any, *, issue_type: str, vehicle_type: str | None) -> tuple[float, list[str]]:
        services = [str(v).lower().replace(" ", "_") for v in (getattr(mechanic, "service_types", None) or [])]
        vehicles = [str(v).lower().replace(" ", "_") for v in (getattr(mechanic, "vehicle_types_supported", None) or [])]
        haystack = " ".join(
            str(v).lower()
            for v in [
                getattr(mechanic, "company_name", ""),
                getattr(mechanic, "address", ""),
                getattr(mechanic, "website", ""),
                " ".join(services),
                " ".join(vehicles),
            ]
            if v
        )
        reasons: list[str] = []
        score = 0.55

        normalized_issue = (issue_type or "").lower().replace(" ", "_")
        if normalized_issue:
            if normalized_issue in services:
                score += 0.30
                reasons.append(f"matches {normalized_issue.replace('_', ' ')}")
            elif any(keyword in haystack for keyword in SERVICE_KEYWORDS.get(normalized_issue, ())):
                score += 0.20
                reasons.append(f"signals {normalized_issue.replace('_', ' ')} capability")
            else:
                score -= 0.12

        normalized_vehicle = (vehicle_type or "").lower().replace(" ", "_")
        if normalized_vehicle:
            if normalized_vehicle in vehicles:
                score += 0.18
                reasons.append(f"supports {normalized_vehicle.replace('_', ' ')}")
            elif any(token in haystack for token in (normalized_vehicle, normalized_vehicle.replace("_", " "))):
                score += 0.10
                reasons.append(f"appears compatible with {normalized_vehicle.replace('_', ' ')}")
            else:
                score -= 0.07

        return round(min(max(score, 0.0), 1.0), 4), reasons

    @staticmethod
    def _roadside_relevance_score(mechanic: Mechanic | Any, require_mobile: bool) -> float:
        score = 0.35
        if bool(getattr(mechanic, "accepts_mobile_roadside", False)):
            score += 0.38
        elif require_mobile:
            score -= 0.20
        if bool(getattr(mechanic, "emergency_service", False)):
            score += 0.17
        if (getattr(mechanic, "service_radius_miles", 0) or 0) >= 50:
            score += 0.10
        return min(max(score, 0.0), 1.0)

    @staticmethod
    def _reliability_score(mechanic: Mechanic | Any) -> float:
        total_dispatches = getattr(mechanic, "total_dispatches", 0) or 0
        successful_dispatches = getattr(mechanic, "successful_dispatches", 0) or 0
        if total_dispatches > 0:
            return min(max(successful_dispatches / total_dispatches, 0.0), 1.0)
        source_confidence = getattr(mechanic, "source_confidence", None) or 0.55
        rating = float(getattr(mechanic, "rating", None) or 3.8) / 5.0
        review_depth = min((getattr(mechanic, "review_count", None) or 0) / 100.0, 1.0)
        return round((source_confidence * 0.35) + (rating * 0.45) + (review_depth * 0.20), 4)

    @staticmethod
    def _availability_score(mechanic: Mechanic | Any) -> tuple[float, str]:
        available_now, status = MechanicDataService._available_now(mechanic)
        if available_now is True:
            return 1.0, status
        if available_now is False:
            return 0.0, status
        if bool(getattr(mechanic, "emergency_service", False)):
            return 0.82, "emergency_service_hours_unconfirmed"
        return 0.55, status

    @staticmethod
    def _review_quality_score(mechanic: Mechanic | Any) -> float:
        rating = float(getattr(mechanic, "rating", None) or 3.6)
        review_count = getattr(mechanic, "review_count", None) or 0
        rating_component = min(max(rating / 5.0, 0.0), 1.0)
        depth_component = min(review_count / 150.0, 1.0)
        return round((rating_component * 0.72) + (depth_component * 0.28), 4)

    @staticmethod
    def _distance_score(distance_miles: float | None, mechanic: Mechanic | Any) -> float:
        if distance_miles is None:
            return 0.62
        service_radius = getattr(mechanic, "service_radius_miles", 50) or 50
        max_radius = max(float(service_radius), 25.0)
        if distance_miles > max_radius:
            return 0.0
        return round(1.0 - (distance_miles / max_radius), 4)

    @staticmethod
    def _fleet_fit_score(mechanic: Mechanic | Any) -> float:
        text = " ".join(
            str(v).lower()
            for v in [
                getattr(mechanic, "company_name", ""),
                " ".join(str(item) for item in (getattr(mechanic, "vehicle_types_supported", None) or [])),
                " ".join(str(item) for item in (getattr(mechanic, "service_types", None) or [])),
            ]
        )
        if any(token in text for token in ("fleet", "semi", "heavy", "diesel", "truck", "trailer")):
            return 1.0
        return 0.55

    @staticmethod
    def _build_reasons(
        mechanic: Mechanic | Any,
        *,
        service_reasons: list[str],
        distance_miles: float | None,
        estimated_response_minutes: int | None,
        trust_score: float,
        availability_status: str,
    ) -> list[str]:
        reasons = list(service_reasons)
        if distance_miles is not None:
            reasons.append(f"{distance_miles:.1f} miles from request")
        if bool(getattr(mechanic, "accepts_mobile_roadside", False)):
            reasons.append("mobile roadside capable")
        if bool(getattr(mechanic, "emergency_service", False)):
            reasons.append("24/7 emergency signal")
        if estimated_response_minutes is not None:
            reasons.append(f"estimated response {estimated_response_minutes} min")
        if trust_score >= 0.78:
            reasons.append("strong trust score")
        elif availability_status == "hours_unknown":
            reasons.append("hours need confirmation")
        return reasons[:5] or ["best deterministic fit for this service area"]

    @staticmethod
    def _build_badges(
        mechanic: Mechanic | Any,
        *,
        trust_score: float,
        response_confidence_score: float,
        roadside_score: float,
    ) -> list[str]:
        badges: list[str] = []
        if roadside_score >= 0.75:
            badges.append("Roadside-ready")
        if bool(getattr(mechanic, "emergency_service", False)):
            badges.append("24/7 signal")
        if trust_score >= 0.8:
            badges.append("Trusted provider")
        if response_confidence_score >= 0.75:
            badges.append("Fast-response fit")
        if (getattr(mechanic, "review_count", None) or 0) >= 50:
            badges.append("Review depth")
        if getattr(mechanic, "email", None) or getattr(mechanic, "website", None):
            badges.append("Enriched profile")
        return badges[:5]

    @staticmethod
    def _trust_level(score: float) -> str:
        if score >= 0.82:
            return "elite"
        if score >= 0.68:
            return "trusted"
        if score >= 0.52:
            return "qualified"
        return "needs_verification"
