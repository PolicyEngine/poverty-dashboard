"""Single-region poverty rate calculation."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from poverty_dashboard.versions import installed_versions

YEAR = 2026
SUPPORTED_YEARS = [2024, 2025, 2026]
US_DATA_ROOT = "hf://policyengine/policyengine-us-data"
US_DATASET_ENV = "POVERTY_DASHBOARD_US_DATASET"


def resolve_dataset(region_code: str) -> str:
    """Resolve a dedicated dataset for the legacy diagnostic scripts.

    A path cannot express state scoping. Those callers must migrate to the
    managed simulation and geographic filtering before supporting states.
    """
    if region_code == "us" and (configured := os.environ.get(US_DATASET_ENV)):
        return configured

    from policyengine.countries.us.regions import us_region_registry

    region = us_region_registry.get(region_code)
    if region is None:
        raise ValueError(f"Unknown region: {region_code}")
    if region.requires_filter or region.dataset_path is None:
        raise ValueError(f"Region {region_code} requires geographic filtering")
    return region.dataset_path


def build_region_simulation(region_code: str) -> tuple[Any, Any]:
    """Load the wrapper's certified population and its region definition.

    Package/data selection belongs to the installed wrapper bundle. The
    explicitly configured local national dataset is an unmanaged diagnostic
    override, whose runtime provenance is retained in the result.
    """
    import policyengine as pe
    from policyengine.core.scoping_strategy import RowFilterStrategy
    from policyengine.countries.us.regions import us_region_registry

    region = us_region_registry.get(region_code)
    if region is None or region.region_type not in {"national", "state"}:
        raise ValueError(f"Unsupported region: {region_code}")
    strategy = region.scoping_strategy
    if region.region_type == "state" and (
        not isinstance(strategy, RowFilterStrategy)
        or strategy.variable_name != "state_fips"
        or strategy.additional_filters
    ):
        raise ValueError(f"Unsupported geographic filtering for {region_code}")
    configured = os.environ.get(US_DATASET_ENV) if region_code == "us" else None
    sim = pe.us.managed_microsimulation(
        dataset=configured, allow_unmanaged=configured is not None
    )
    return sim, region


def require_scoping_variable_input(sim: Any, strategy: Any) -> None:
    """Refuse to filter on a variable this population never supplied.

    ``state_fips`` is a formula-less Household input defaulting to 6
    (California), policyengine-core drops dataset columns that are not system
    variables, and a variable with no known period falls back to its default
    array. A population that dropped or renamed the column would therefore put
    every household in California and none in the other 50 states. Ask before
    calculating: calculating the variable caches a period and hides the gap.
    """
    if not sim.get_known_periods(strategy.variable_name):
        raise ValueError(
            f"{strategy.variable_name} is not an input in this population, so "
            "region filtering would read its default value"
        )


def require_discriminating_scope(values: Any, strategy: Any) -> None:
    """Refuse to filter on a column holding one value for the whole country."""
    if values.nunique() < 2:
        raise ValueError(
            f"{strategy.variable_name} holds a single value across this "
            "population, so region filtering cannot separate regions"
        )


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
    if year not in SUPPORTED_YEARS:
        raise ValueError(
            f"Unsupported year: {year}. Expected one of {SUPPORTED_YEARS}."
        )

    sim, region = build_region_simulation(region_code)
    strategy = region.scoping_strategy
    if strategy is not None:
        require_scoping_variable_input(sim, strategy)
    provenance = dict(sim.policyengine_bundle)

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

    if strategy is not None:
        scope = sim.calculate(strategy.variable_name, period=year, map_to="person")
        require_discriminating_scope(scope, strategy)
        in_region = scope == strategy.variable_value
        if not in_region.any():
            raise ValueError(f"No people in dataset for {region_code}")
        age = age[in_region]
        in_poverty = in_poverty[in_region]
        in_deep_poverty = in_deep_poverty[in_region]

    return {
        "region_code": region_code,
        "dataset_path": provenance["runtime_dataset_uri"],
        "policyengine_bundle": provenance,
        "region_scope": strategy.model_dump(mode="json") if strategy else None,
        "versions": installed_versions(),
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
