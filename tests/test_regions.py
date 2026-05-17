from __future__ import annotations

import pytest

from poverty_dashboard.regions import all_region_codes, region_label, region_state_code


def test_all_region_codes_contains_national_and_states() -> None:
    codes = all_region_codes()

    assert codes[0] == "us"
    assert len(codes) == 52
    assert "state/ca" in codes
    assert "state/dc" in codes


def test_region_label_and_state_code() -> None:
    assert region_label("us") == "United States"
    assert region_state_code("us") is None
    assert region_label("state/ny") == "New York"
    assert region_state_code("state/ny") == "NY"


def test_region_helpers_reject_unknown_regions() -> None:
    with pytest.raises(ValueError, match="Unknown state region"):
        region_label("state/zz")

    with pytest.raises(ValueError, match="Unsupported region"):
        region_state_code("county/001")
