import re


STATE_NAME_TO_CODE = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}


def normalize_city(city: str | None) -> str | None:
    if not city:
        return None
    cleaned = re.sub(r"\s+", " ", city.strip())
    return cleaned.title() if cleaned else None


def normalize_state(state: str | None) -> str | None:
    if not state:
        return None
    cleaned = state.strip()
    if not cleaned:
        return None

    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()

    return STATE_NAME_TO_CODE.get(cleaned.lower())


def parse_city_state_from_address(address: str | None) -> tuple[str | None, str | None]:
    if not address:
        return None, None

    parts = [part.strip() for part in address.split(",") if part.strip()]
    if len(parts) < 2:
        return None, None

    # Common US formats:
    #   "123 Main St, Orlando, FL 32803"
    #   "123 Main St, Orlando, FL, USA"
    #   "123 Main St, Orlando, Florida"
    # Find the state part from the right, then use the comma part immediately
    # before it as city. The previous implementation picked parts[-3], which
    # incorrectly saved street addresses as city for "street, city, ST zip".
    city = None
    state = None
    for index in range(len(parts) - 1, -1, -1):
        part = parts[index]
        state_match = re.search(r"\b([A-Z]{2})\b", part)
        maybe_state = normalize_state(state_match.group(1) if state_match else part)
        if maybe_state:
            state = maybe_state
            if index > 0:
                city = normalize_city(parts[index - 1])
            break

    if not city and len(parts) >= 2:
        city = normalize_city(parts[-2])

    return city, state


def city_matches(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return normalize_city(left) == normalize_city(right)