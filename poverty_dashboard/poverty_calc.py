"""Single-region poverty rate calculation."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from poverty_dashboard.regions import region_state_code

YEAR = 2026
SUPPORTED_YEARS = [2024, 2025, 2026]
US_DATA_ROOT = "hf://policyengine/policyengine-us-data"
US_DATASET_ENV = "POVERTY_DASHBOARD_US_DATASET"


def fallback_dataset(region_code: str) -> str:
    """Return the documented Hugging Face dataset path for a region."""
    if region_code == "us":
        if configured := os.environ.get(US_DATASET_ENV):
            return configured
        return f"{US_DATA_ROOT}/enhanced_cps_2024.h5"

    abbrev = region_state_code(region_code)
    if abbrev is None:
        raise ValueError(f"Unsupported region: {region_code}")
    return f"{US_DATA_ROOT}/states/{abbrev}.h5"


def resolve_dataset(region_code: str) -> str:
    """Resolve the dataset path using PolicyEngine's US region registry."""
    if region_code == "us" and (configured := os.environ.get(US_DATASET_ENV)):
        return configured

    try:
        from policyengine.countries.us.regions import us_region_registry  # type: ignore
    except Exception:
        return fallback_dataset(region_code)

    region = us_region_registry.get(region_code)
    if region is None:
        raise ValueError(f"Unknown region: {region_code}")
    return region.dataset_path


def summarize_poverty(
    age: Any, in_poverty: Any, in_deep_poverty: Any
) -> dict[str, Any]:
    """Summarize person-level poverty rates using weighted MicroSeries operations."""
    is_person = age >= 0
    is_child = age < 18
    is_working_age = (age >= 18) & (age < 65)
    is_senior = age >= 65

    return {
        "people": float(is_person.sum()),
        "child_count": float(is_child.sum()),
        "rates": {
            "all": float(in_poverty.mean()),
            "child": float(in_poverty[is_child].mean()),
            "working_age": float(in_poverty[is_working_age].mean()),
            "senior": float(in_poverty[is_senior].mean()),
        },
        "deep_rates": {
            "all": float(in_deep_poverty.mean()),
            "child": float(in_deep_poverty[is_child].mean()),
            "working_age": float(in_deep_poverty[is_working_age].mean()),
            "senior": float(in_deep_poverty[is_senior].mean()),
        },
    }


def compute_region(region_code: str, year: int = YEAR) -> dict[str, Any]:
    """Compute baseline poverty rates for one region."""
    from policyengine_us import Microsimulation

    if year not in SUPPORTED_YEARS:
        raise ValueError(
            f"Unsupported year: {year}. Expected one of {SUPPORTED_YEARS}."
        )

    dataset_path = resolve_dataset(region_code)
    sim = Microsimulation(dataset=dataset_path)

    age = sim.calculate("age", period=year)
    in_poverty = sim.calculate(
        "spm_unit_is_in_spm_poverty",
        period=year,
        map_to="person",
    )
    in_deep_poverty = sim.calculate(
        "spm_unit_is_in_deep_spm_poverty",
        period=year,
        map_to="person",
    )

    return {
        "region_code": region_code,
        "dataset_path": dataset_path,
        "year": year,
        **summarize_poverty(age, in_poverty, in_deep_poverty),
    }


def main() -> None:
    """Run the single-region calculation CLI."""
    if len(sys.argv) < 2:
        print(
            "usage: python -m poverty_dashboard.poverty_calc <region_code> [year]",
            file=sys.stderr,
        )
        sys.exit(2)
    year = int(sys.argv[2]) if len(sys.argv) > 2 else YEAR
    result = compute_region(sys.argv[1], year=year)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
