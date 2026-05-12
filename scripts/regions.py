"""Region codes mirrored from policyengine.countries.us.regions.

The 51 state regions plus the national region. Each entry maps directly to the
dataset path resolved by ``us_region_registry`` inside the worker, so the
dashboard runs the same data the API would for that region.
"""

from __future__ import annotations

US_STATES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def all_region_codes() -> list[str]:
    """National + 51 state region codes, in the policyengine.py format."""
    return ["us"] + [f"state/{abbrev.lower()}" for abbrev in US_STATES]


def region_label(region_code: str) -> str:
    if region_code == "us":
        return "United States"
    abbrev = region_code.split("/", 1)[1].upper()
    return US_STATES[abbrev]


def region_state_code(region_code: str) -> str | None:
    if region_code == "us":
        return None
    return region_code.split("/", 1)[1].upper()
