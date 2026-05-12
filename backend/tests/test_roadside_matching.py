from app.schemas.roadside_match import RoadsideCallerContext, RoadsideLocationInput, RoadsideMatchRequest
from app.api.routes import roadside
from app.services.roadside_matching_service import (
    RoadsideMatchingService,
    classifyProblem,
    createManualDispatchFallback,
    findExactCityMatches,
    findMechanicsByStateCity,
    findRadiusMatches,
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


def test_city_problem_without_vehicle_type_asks_vehicle_before_search():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(message="I'm in Lakeland Florida and need a tow")
    )

    assert context.city == "Lakeland"
    assert context.state == "FL"
    assert context.problemType == "tow_needed"
    assert RoadsideMatchingService.missing_fields(context) == ["vehicleType"]
    assert RoadsideMatchingService.next_question(["vehicleType"]) == "What type of vehicle is it — car, pickup, box truck, semi, trailer, RV, or fleet vehicle?"


def test_vehicle_type_is_parsed_from_caller_message():
    context = RoadsideMatchingService.build_context(
        RoadsideMatchRequest(message="I'm in Lakeland Florida with an RV that needs towing")
    )

    assert context.vehicleType == "rv"
    assert RoadsideMatchingService.missing_fields(context) == []


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


def test_city_level_match_message_lists_options_and_asks_choice():
    context = RoadsideCallerContext(
        city="Lakeland",
        state="FL",
        problemType="flat_tire",
        serviceNeeded="tire repair",
    )
    mechanics = [
        make_test_mechanic(id="a", company_name="Alpha Tire", city="Lakeland", state="FL"),
        make_test_mechanic(id="b", company_name="Bravo Roadside", city="Lakeland", state="FL"),
        make_test_mechanic(id="c", company_name="Charlie Mobile", city="Lakeland", state="FL"),
    ]
    formatted = formatDispatchRecommendation(
        rankMechanics([(mechanic, scoreMechanicMatch(mechanic, context)) for mechanic in mechanics])
    )

    assert RoadsideMatchingService._is_city_level_request(context) is True
    message = RoadsideMatchingService.match_message(
        context=context,
        matches=formatted,
        search_level="exact_city",
        city_level_request=True,
    )

    assert "I found a few matching mechanics near Lakeland, FL" in message
    assert "1)" in message and "2)" in message and "3)" in message
    assert "text you a secure GPS link" in message
    assert "exact road, exit, or landmark" in message
    assert "start with one of these matches" in message


def test_precise_location_match_message_keeps_distance_options():
    context = RoadsideCallerContext(
        latitude=28.0395,
        longitude=-81.9498,
        city="Lakeland",
        state="FL",
        problemType="tow_needed",
        serviceNeeded="towing",
    )
    mechanics = [
        make_test_mechanic(id="near", company_name="Near Tow", base_lat=28.04, base_lng=-81.95, service_types=["tow_needed"]),
        make_test_mechanic(id="far", company_name="Far Tow", base_lat=28.2, base_lng=-82.1, service_types=["tow_needed"]),
    ]
    formatted = formatDispatchRecommendation(
        rankMechanics([(mechanic, scoreMechanicMatch(mechanic, context)) for mechanic in mechanics])
    )

    assert RoadsideMatchingService._is_city_level_request(context) is False
    message = RoadsideMatchingService.match_message(
        context=context,
        matches=formatted,
        search_level="radius_25_miles",
        city_level_request=False,
    )

    assert "I found nearby roadside matches" in message
    assert "miles away" in message
    assert "text the GPS link" in message


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


def test_vehicle_type_match_ranks_rv_provider_over_heavy_duty_for_rv_call():
    context = RoadsideCallerContext(
        city="Lakeland",
        state="FL",
        problemType="tow_needed",
        serviceNeeded="towing",
        vehicleType="rv",
    )
    rv_provider = make_test_mechanic(
        id="rv",
        company_name="RV Roadside",
        city="Lakeland",
        state="FL",
        service_types=["tow_needed"],
        vehicle_types_supported=["rv", "motorhome"],
    )
    heavy_provider = make_test_mechanic(
        id="heavy",
        company_name="Heavy Diesel Tow",
        city="Lakeland",
        state="FL",
        service_types=["tow_needed"],
        vehicle_types_supported=["heavy_duty", "semi"],
    )

    ranked = rankMechanics(
        [(m, scoreMechanicMatch(m, context)) for m in [heavy_provider, rv_provider]]
    )

    assert ranked[0][0].id == "rv"
    assert "Vehicle type match" in ranked[0][1].reasons


def test_vehicle_type_match_ranks_light_duty_provider_for_car_call():
    context = RoadsideCallerContext(
        city="Orlando",
        state="FL",
        problemType="dead_battery",
        serviceNeeded="battery",
        vehicleType="pickup truck",
    )
    light_provider = make_test_mechanic(
        id="light",
        company_name="Light Duty Roadside",
        city="Orlando",
        state="FL",
        service_types=["dead_battery"],
        vehicle_types_supported=["light_duty", "pickup", "car"],
    )
    trailer_provider = make_test_mechanic(
        id="trailer",
        company_name="Trailer Repair Only",
        city="Orlando",
        state="FL",
        service_types=["dead_battery"],
        vehicle_types_supported=["trailer", "heavy_duty"],
    )

    ranked = rankMechanics(
        [(m, scoreMechanicMatch(m, context)) for m in [trailer_provider, light_provider]]
    )

    assert ranked[0][0].id == "light"
    assert "Vehicle type match" in ranked[0][1].reasons


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


def test_generic_phone_ready_mechanic_not_filtered_out_when_service_labels_are_imperfect():
    context = RoadsideCallerContext(
        city="Lakeland",
        state="FL",
        problemType="flat_tire",
        serviceNeeded="tire repair",
    )
    generic_shop = make_test_mechanic(
        id="generic",
        city="Lakeland",
        state="FL",
        service_types=["roadside assistance"],
        phone="+18635551212",
    )

    matches = findExactCityMatches([generic_shop], "Lakeland", "FL", context.problemType)

    assert [mechanic.id for mechanic in matches] == ["generic"]


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


def test_nearby_city_match_within_25_miles():
    mechanics = [
        make_test_mechanic(id="plant_city", city="Plant City", state="FL", base_lat=28.0186, base_lng=-82.1129, service_types=["tire repair"]),
    ]

    matches = findRadiusMatches(mechanics, 28.0395, -81.9498, "FL", "flat_tire", 25)

    assert [mechanic.id for mechanic in matches] == ["plant_city"]


def test_radius_returns_generic_mechanic_when_no_exact_service_label():
    mechanics = [
        make_test_mechanic(id="plant_city", city="Plant City", state="FL", base_lat=28.0186, base_lng=-82.1129, service_types=["mobile mechanic"]),
    ]

    matches = findRadiusMatches(mechanics, 28.0395, -81.9498, "FL", "flat_tire", 25)

    assert [mechanic.id for mechanic in matches] == ["plant_city"]


def test_nearby_city_match_within_50_miles():
    mechanics = [
        make_test_mechanic(id="tampa", city="Tampa", state="FL", base_lat=27.9506, base_lng=-82.4572, service_types=["tire repair"]),
    ]

    matches = findRadiusMatches(mechanics, 28.0395, -81.9498, "FL", "flat_tire", 50)

    assert [mechanic.id for mechanic in matches] == ["tampa"]


def test_nearby_city_match_within_100_miles():
    mechanics = [
        make_test_mechanic(id="orlando", city="Orlando", state="FL", base_lat=28.5383, base_lng=-81.3792, service_types=["tire repair"], service_radius_miles=50),
    ]

    matches = findRadiusMatches(mechanics, 28.0395, -81.9498, "FL", "flat_tire", 100)

    assert [mechanic.id for mechanic in matches] == ["orlando"]


def test_no_mechanic_found_creates_manual_fallback_result():
    context = RoadsideCallerContext(city="Lakeland", state="FL", problemType="flat_tire")

    fallback = createManualDispatchFallback(context)

    assert fallback.fallback_created is True
    assert fallback.search_level == "radius_100_miles"
    assert fallback.mechanics == []


def test_mechanic_without_phone_excluded_from_radius_matches():
    mechanics = [
        make_test_mechanic(id="no_phone", city="Plant City", state="FL", base_lat=28.0186, base_lng=-82.1129, phone="", service_types=["tire repair"]),
    ]

    matches = findRadiusMatches(mechanics, 28.0395, -81.9498, "FL", "flat_tire", 25)

    assert matches == []


def test_mechanic_outside_current_radius_and_service_radius_excluded():
    mechanics = [
        make_test_mechanic(id="too_far", city="Miami", state="FL", base_lat=25.7617, base_lng=-80.1918, service_radius_miles=25, service_types=["tire repair"]),
    ]

    matches = findRadiusMatches(mechanics, 28.0395, -81.9498, "FL", "flat_tire", 100)

    assert matches == []


async def test_api_error_returns_manual_dispatch_not_hangup(monkeypatch):
    async def broken_match(db, request):
        raise RuntimeError("database timeout")

    monkeypatch.setattr(roadside.RoadsideMatchingService, "match_mechanic", broken_match)

    response = await roadside.match_mechanic(
        RoadsideMatchRequest(message="I'm in Lakeland Florida with a blown tire"),
        db=None,
    )

    assert response.status == "manual_dispatch_required"
    assert response.fallbackCreated is True
    assert response.fallbackEscalation is True
    assert "still create a dispatch request" in response.message