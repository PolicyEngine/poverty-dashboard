from __future__ import annotations

from poverty_dashboard.regions import all_region_codes
from scripts.regions import all_region_codes as old_all_region_codes


def test_scripts_region_wrapper_matches_package_api() -> None:
    assert old_all_region_codes() == all_region_codes()
