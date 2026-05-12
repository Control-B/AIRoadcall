from app.utils.location import parse_city_state_from_address


def test_parse_city_state_from_street_city_state_zip():
    city, state = parse_city_state_from_address("924 N Magnolia Ave 202 Unit #5035, Orlando, FL 32803")
    assert city == "Orlando"
    assert state == "FL"


def test_parse_city_state_from_city_state_country_format():
    city, state = parse_city_state_from_address("2350 Diversified Way, Orlando, FL, USA")
    assert city == "Orlando"
    assert state == "FL"


def test_parse_city_state_from_full_state_name():
    city, state = parse_city_state_from_address("4106 S 50th St, Tampa, Florida")
    assert city == "Tampa"
    assert state == "FL"
