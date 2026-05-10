from app.schemas.roadside_match import RoadsideCallerContext, RoadsideLocationInput, RoadsideMatchRequest
from app.services.roadside_matching_service import (
    RoadsideMatchingService,
    classifyProblem,
    findMechanicsByStateCity,
    formatDispatchRecommendation,
    make_test_mechanic,
    parseCallerLocation,
    rankMechanics,
    scoreMechanicMatch,
)


def test_parse_city_state_from_voice_text():
    parsed = parseCallerLocation("I'm in Dallas Texas with a flat tire")

    assert parsed["city"] == "Dallas"
    assert parsed["state"] == "TX"


def test_parse_highway_city_state_location():
    parsed = parseCallerLocation("I'm on I-75 near Tampa FL at exit 261")

    assert parsed["road"].upper().replace(" ", "").replace("-", "") == "I75"
    assert parsed["city"] == "Tampa"
    assert parsed["state"] == "FL"
    assert parsed["landmark"] == "261"


def test_vague_location_requires_more_detail():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(message="I'm somewhere on the shoulder with a flat tire")
    )

    assert RoadsideMatchingService.missing_fields(context) == ["location", "state"]
    assert RoadsideMatchingService.next_question(["location", "state"]) == "What city or nearest exit?"


def test_gps_coordinates_are_used_for_distance_scoring():
    context = RoadsideCallerContext(
        latitude=27.9506,
        longitude=-82.4572,
        state="FL",
        problemType="flat_tire",
        serviceNeeded="tire repair",
        vehicleType="semi truck",
    )
    mechanic = make_test_mechanic(base_lat=27.9506, base_lng=-82.4572)

    scored = scoreMechanicMatch(mechanic, context)

    assert scored.distance_miles is not None
    assert scored.distance_miles < 0.1
    assert "Within 50 mile service radius" in scored.reasons


def test_problem_but_no_location_needs_location():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(message="I have a blown steer tire")
    )

    assert context.problemType == "flat_tire"
    assert "location" in RoadsideMatchingService.missing_fields(context)


def test_location_but_vague_problem_needs_problem_type():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(message="I'm in Phoenix AZ and need help")
    )

    assert context.city == "Phoenix"
    assert context.state == "AZ"
    assert RoadsideMatchingService.missing_fields(context) == ["problemType"]


def test_same_state_fallback_scores_when_city_does_not_match():
    context = RoadsideCallerContext(
        city="Smalltown",
        state="TX",
        problemType="engine_trouble",
        serviceNeeded="diesel repair",
        vehicleType="semi",
    )
    mechanic = make_test_mechanic(city="Dallas", state="TX", service_types=["engine_trouble"])

    scored = scoreMechanicMatch(mechanic, context)

    assert "Same state fallback match" in scored.reasons
    assert scored.score > 0


def test_no_state_match_is_missing_state():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(message="I'm near exit 55 with a dead battery")
    )

    assert context.landmark == "55"
    assert "state" in RoadsideMatchingService.missing_fields(context)


def test_multiple_mechanics_rank_by_service_priority_and_fit():
    context = RoadsideCallerContext(
        city="Dallas",
        state="TX",
        problemType="flat_tire",
        serviceNeeded="tire repair",
        vehicleType="semi truck",
    )
    best = make_test_mechanic(
        id="best",
        company_name="Best Tire",
        city="Dallas",
        state="TX",
        service_types=["flat_tire"],
        priority_score=95,
    )
    weaker = make_test_mechanic(
        id="weaker",
        company_name="General Shop",
        city="Dallas",
        state="TX",
        service_types=["engine_trouble"],
        priority_score=10,
    )

    ranked = rankMechanics([(m, scoreMechanicMatch(m, context)) for m in [weaker, best]])
    formatted = formatDispatchRecommendation(ranked)

    assert formatted[0].mechanicId == "best"
    assert formatted[0].businessName == "Best Tire"
    assert "Service match" in formatted[0].reason


def test_emergency_mobile_mechanic_ranks_higher():
    context = RoadsideCallerContext(
        city="Tampa",
        state="FL",
        problemType="flat_tire",
        serviceNeeded="tire repair",
        vehicleType="semi",
    )
    emergency_mobile = make_test_mechanic(id="emergency_mobile", emergency_service=True, accepts_mobile_roadside=True)
    shop_only = make_test_mechanic(id="shop_only", emergency_service=False, accepts_mobile_roadside=False)

    ranked = rankMechanics(
        [(m, scoreMechanicMatch(m, context)) for m in [shop_only, emergency_mobile]]
    )

    assert ranked[0][0].id == "emergency_mobile"
    assert "24/7 emergency availability" in ranked[0][1].reasons
    assert "Mobile roadside service" in ranked[0][1].reasons


def test_find_mechanics_by_state_city_groups_dataset_shape():
    mechanics = [
        make_test_mechanic(id="tx", city="Dallas", state="TX"),
        make_test_mechanic(id="fl", city="Tampa", state="FL"),
    ]

    matches = findMechanicsByStateCity(mechanics, "texas", "dallas")

    assert [mechanic.id for mechanic in matches] == ["tx"]


def test_find_mechanics_by_state_city_matches_common_city_aliases():
    mechanics = [
        make_test_mechanic(id="stp", city="St Petersburg", state="FL"),
        make_test_mechanic(id="tpa", city="Tampa", state="FL"),
    ]

    matches = findMechanicsByStateCity(mechanics, "FL", "Saint Petersburg")

    assert [mechanic.id for mechanic in matches] == ["stp"]


def test_score_matches_human_readable_service_type():
    context = RoadsideCallerContext(
        city="Saint Petersburg",
        state="FL",
        problemType="flat_tire",
        serviceNeeded="tire repair",
        vehicleType="semi truck",
    )
    mechanic = make_test_mechanic(city="St. Petersburg", state="FL", service_types=["Tire Repair"])

    scored = scoreMechanicMatch(mechanic, context)

    assert "Exact city/state match" in scored.reasons
    assert "Service match for tire repair" in scored.reasons


def test_structured_location_overrides_transcript():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(
            message="I'm around Dallas TX with a battery issue",
            location=RoadsideLocationInput(city="Fort Worth", state="TX"),
        )
    )

    assert context.city == "Fort Worth"
    assert context.state == "TX"
    assert context.problemType == "dead_battery"


def test_caller_phone_is_preserved_for_sms_location_flow():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(
            message="I'm in Dallas TX with a flat tire",
            callerPhone="(214) 555-1212",
        )
    )

    assert context.callerPhone == "2145551212"
    assert context.callbackNumber == "2145551212"