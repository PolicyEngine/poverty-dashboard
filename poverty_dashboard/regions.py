"""Region codes mirrored from ``policyengine.countries.us.regions``."""

from __future__ import annotations

US_STATES: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def all_region_codes() -> list[str]:
    """Return national plus state region codes in policyengine.py format."""
    return ["us", *[f"state/{abbrev.lower()}" for abbrev in US_STATES]]


def region_label(region_code: str) -> str:
    """Return a human-readable label for a PolicyEngine US region code."""
    if region_code == "us":
        return "United States"
    return US_STATES[_state_abbrev(region_code)]


def region_state_code(region_code: str) -> str | None:
    """Return the two-letter state code for state regions, else ``None``."""
    if region_code == "us":
        return None
    return _state_abbrev(region_code)


def _state_abbrev(region_code: str) -> str:
    if not region_code.startswith("state/"):
        raise ValueError(f"Unsupported region: {region_code}")

    abbrev = region_code.split("/", 1)[1].upper()
    if abbrev not in US_STATES:
        raise ValueError(f"Unknown state region: {region_code}")
    return abbrev
