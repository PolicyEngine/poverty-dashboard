"""Single-region poverty rate calculation.

Mirrors policyengine-api's methodology exactly:

  1. Resolve the dataset for the region via ``us_region_registry`` — same path
     the API hands to its simulation backend.
  2. Build a ``policyengine_us.Microsimulation`` against that dataset.
  3. Take the weighted mean of ``person_in_poverty`` and
     ``person_in_deep_poverty``, filtering ``age < 18`` for child rates.

Designed to be invoked as ``python -m scripts.poverty_calc <region_code>`` so a
fresh interpreter sees freshly-installed package versions on each call.
"""

from __future__ import annotations

import json
import sys
from typing import Any


YEAR = 2026

US_DATA_ROOT = "hf://policyengine/policyengine-us-data"


def _resolve_dataset(region_code: str) -> str:
    """Mirror policyengine.countries.us.regions dataset routing.

    Tries the registry first; on import failure (e.g. an editable
    policyengine.py with a mismatched policyengine-us manifest), falls back to
    the documented HuggingFace URL convention.
    """
    try:
        from policyengine.countries.us.regions import us_region_registry  # type: ignore
        region = us_region_registry.get(region_code)
        if region is None:
            raise ValueError(f"Unknown region: {region_code}")
        return region.dataset_path
    except Exception:
        pass

    if region_code == "us":
        return f"{US_DATA_ROOT}/enhanced_cps_2024.h5"
    if region_code.startswith("state/"):
        abbrev = region_code.split("/", 1)[1].upper()
        return f"{US_DATA_ROOT}/states/{abbrev}.h5"
    raise ValueError(f"Unsupported region: {region_code}")


def compute_region(region_code: str, year: int = YEAR) -> dict[str, Any]:
    """Compute baseline poverty rates for one region, returning a JSON-safe dict."""
    from microdf import MicroSeries
    from policyengine_us import Microsimulation

    dataset_path = _resolve_dataset(region_code)
    sim = Microsimulation(dataset=dataset_path)

    age = sim.calculate("age", period=year).values
    weights = sim.calculate("person_weight", period=year).values
    # Canonical policyengine.py variable names (see policyengine/outputs/poverty.py
    # USPovertyType.SPM / SPM_DEEP). Mapped from spm_unit to person to match
    # the API methodology of person-level weighted poverty rates.
    in_poverty = sim.calculate(
        "spm_unit_is_in_spm_poverty", period=year, map_to="person"
    ).values
    in_deep_poverty = sim.calculate(
        "spm_unit_is_in_deep_spm_poverty", period=year, map_to="person"
    ).values

    poverty = MicroSeries(in_poverty, weights=weights)
    deep_poverty = MicroSeries(in_deep_poverty, weights=weights)
    is_child = age < 18
    is_working_age = (age >= 18) & (age < 65)
    is_senior = age >= 65

    return {
        "region_code": region_code,
        "dataset_path": dataset_path,
        "year": year,
        "people": float(weights.sum()),
        "child_count": float(weights[is_child].sum()),
        "rates": {
            "all": float(poverty.mean()),
            "child": float(poverty[is_child].mean()),
            "working_age": float(poverty[is_working_age].mean()),
            "senior": float(poverty[is_senior].mean()),
        },
        "deep_rates": {
            "all": float(deep_poverty.mean()),
            "child": float(deep_poverty[is_child].mean()),
            "working_age": float(deep_poverty[is_working_age].mean()),
            "senior": float(deep_poverty[is_senior].mean()),
        },
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m scripts.poverty_calc <region_code>", file=sys.stderr)
        sys.exit(2)
    result = compute_region(sys.argv[1])
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
