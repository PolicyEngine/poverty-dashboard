"""SPM diagnostics comparing PolicyEngine output with Census report aggregates."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pandas as pd
from microdf import MicroSeries

from poverty_dashboard.paths import DATA_DIR
from poverty_dashboard.poverty_calc import US_DATA_ROOT, resolve_dataset
from poverty_dashboard.spm_elements import (
    AGE_GROUPS,
    compute_spm_element_effects,
    poverty_rates,
    spm_unit_component_as_person,
)

TABLES_PAGE = "https://www.census.gov/data/tables/2025/demo/income-poverty/p60-287.html"
TABLE_B2 = "https://www2.census.gov/programs-surveys/demo/tables/p60/287/tableB-2.xlsx"
TABLE_B5 = "https://www2.census.gov/programs-surveys/demo/tables/p60/287/tableB-5.xlsx"
TABLE_B6 = "https://www2.census.gov/programs-surveys/demo/tables/p60/287/tableB-6.xlsx"
BLS_2024_THRESHOLDS = "https://www.bls.gov/pir/spm/spm_thresholds_2024.htm"
CENSUS_TAX_MODEL = (
    "https://www.census.gov/topics/income-poverty/income/guidance/tax-model.html"
)
CENSUS_SPM_TECHDOC = (
    "https://www2.census.gov/programs-surveys/supplemental-poverty-measure/"
    "datasets/spm/spm_techdoc.pdf"
)
OCSS_2024_PRELIMINARY = (
    "https://acf.gov/css/policy-guidance/fy-2024-preliminary-data-report-and-tables"
)
LIHEAP_2024_PROFILE = (
    "https://liheappm.acf.gov/sites/default/files/private/congress/profiles/"
    "2024/FY2024_AllStates%28National%29_Profile.pdf"
)
NASI_WORKERS_COMP_2022 = (
    "https://www.nasi.org/wp-content/uploads/2024/11/"
    "Sources-Methods-and-State-Summaries-2022-Data-Report-FINAL-2024_11_13.pdf"
)
NCCI_2024_SOTL = "https://www.ncci.com/Articles/Pages/Insights-AIS2024-SOTL.aspx"
NCCI_2025_SOTL = "https://www.ncci.com/Articles/Pages/Insights-AIS2025-SOTL.aspx"

DATA_CENSUS_SPM_2024 = DATA_DIR / "census_spm_2024.json"
DEFAULT_DIAGNOSTICS = DATA_DIR / "spm_gap_diagnostics.json"
RAW_CPS_ASEC_2024 = f"{US_DATA_ROOT}/cps_2024.h5"
CENSUS_ASEC_2024_ZIP = (
    "https://www2.census.gov/programs-surveys/cps/datasets/2025/march/asecpub25csv.zip"
)
CENSUS_ASEC_2024_PERSON_FILE = "pppub25.csv"

RatioBin = tuple[str, str, float | None, float | None]

THRESHOLD_RATIO_BINS: tuple[RatioBin, ...] = (
    ("less_than_0_50", "Less than 0.50", None, 0.50),
    ("from_0_50_to_0_99", "0.50 to 0.99", 0.50, 1.00),
    ("from_1_00_to_1_49", "1.00 to 1.49", 1.00, 1.50),
    ("from_1_50_to_1_99", "1.50 to 1.99", 1.50, 2.00),
    ("from_2_00_to_3_99", "2.00 to 3.99", 2.00, 4.00),
    ("from_4_00_or_more", "4.00 or more", 4.00, None),
)

RESOURCE_MEAN_VARIABLES: tuple[str, ...] = (
    "spm_unit_net_income",
    "spm_unit_market_income",
    "spm_unit_spm_threshold",
    "spm_unit_benefits",
    "spm_unit_taxes",
    "spm_unit_spm_expenses",
    "spm_unit_medical_out_of_pocket_expenses",
    "child_support_received",
    "workers_compensation",
    "miscellaneous_income",
    "alimony_income",
    "strike_benefits",
    "educational_assistance",
    "financial_assistance",
    "survivor_benefits",
    "spm_unit_energy_subsidy",
)

ENHANCED_NEGATIVE_INCOME_VARIABLE_CANDIDATES: tuple[str, ...] = ("spm_unit_net_income",)

RAW_NEGATIVE_INCOME_VARIABLE_CANDIDATES: tuple[str, ...] = (
    "spm_unit_net_income_reported",
    "spm_unit_net_income",
)

SOURCE_REPLICATION_COMPONENTS: tuple[tuple[str, str], ...] = (
    ("spm_unit_net_income", "Modeled SPM resources"),
    ("spm_unit_market_income", "Market income"),
    ("employment_income", "Employment income"),
    ("pension_income", "Pension income"),
    ("retirement_distributions", "Retirement distributions"),
    ("interest_income", "Interest income"),
    ("capital_gains", "Capital gains"),
    ("farm_operations_income", "Farm operations income"),
    ("spm_unit_taxes", "Taxes"),
    ("spm_unit_spm_expenses", "SPM expenses"),
    ("spm_unit_medical_out_of_pocket_expenses", "Medical expenses"),
    ("spm_unit_capped_work_childcare_expenses", "Work and childcare expenses"),
    ("child_support_received", "Child support received"),
    ("workers_compensation", "Workers' compensation"),
    ("miscellaneous_income", "Other catch-all income"),
    ("alimony_income", "Alimony income"),
    ("strike_benefits", "Strike benefits"),
    ("educational_assistance", "Educational assistance"),
    ("financial_assistance", "Financial assistance"),
    ("survivor_benefits", "Survivor benefits"),
    ("spm_unit_energy_subsidy", "Energy assistance"),
    ("spm_unit_capped_housing_subsidy", "Housing subsidy"),
)

CPS_TOTAL_INCOME_LEAF_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        "key": "employment_income",
        "label": "Wage and salary income",
        "raw_columns": ("WSAL_VAL",),
        "enhanced_variables": ("employment_income",),
    },
    {
        "key": "self_employment_income",
        "label": "Non-farm self-employment income",
        "raw_columns": ("SEMP_VAL",),
        "enhanced_variables": ("self_employment_income",),
    },
    {
        "key": "farm_operations_income",
        "label": "Farm self-employment income",
        "raw_columns": ("FRSE_VAL",),
        "enhanced_variables": ("farm_operations_income",),
    },
    {
        "key": "interest_income",
        "label": "Interest income",
        "raw_columns": ("INT_VAL",),
        "enhanced_variables": ("interest_income",),
    },
    {
        "key": "dividend_income",
        "label": "Dividend income",
        "raw_columns": ("DIV_VAL",),
        "enhanced_variables": ("dividend_income",),
    },
    {
        "key": "rental_income",
        "label": "Rental income",
        "raw_columns": ("RNT_VAL",),
        "enhanced_variables": ("rental_income",),
    },
    {
        "key": "social_security",
        "label": "Social Security",
        "raw_columns": ("SS_VAL",),
        "enhanced_variables": ("social_security",),
    },
    {
        "key": "unemployment_compensation",
        "label": "Unemployment compensation",
        "raw_columns": ("UC_VAL",),
        "enhanced_variables": ("unemployment_compensation",),
    },
    {
        "key": "pension_income",
        "label": "Pensions and annuities",
        "raw_columns": ("PNSN_VAL", "ANN_VAL"),
        "enhanced_variables": ("pension_income",),
    },
    {
        "key": "other_income",
        "label": "Other catch-all income",
        "raw_columns": ("OI_VAL",),
        "enhanced_variables": (
            "miscellaneous_income",
            "alimony_income",
            "strike_benefits",
        ),
    },
    {
        "key": "child_support_received",
        "label": "Child support received",
        "raw_columns": ("CSP_VAL",),
        "enhanced_variables": ("child_support_received",),
    },
    {
        "key": "public_assistance",
        "label": "Public assistance/welfare",
        "raw_columns": ("PAW_VAL",),
        "enhanced_variables": ("tanf",),
    },
    {
        "key": "ssi",
        "label": "SSI",
        "raw_columns": ("SSI_VAL",),
        "enhanced_variables": ("ssi",),
    },
    {
        "key": "retirement_distributions",
        "label": "Retirement distributions",
        "raw_columns": ("DBTN_VAL",),
        "enhanced_variables": ("retirement_distributions",),
    },
    {
        "key": "disability_benefits",
        "label": "Disability benefits",
        "raw_columns": ("DSAB_VAL",),
        "enhanced_variables": ("disability_benefits",),
    },
    {
        "key": "education_assistance",
        "label": "Educational assistance",
        "raw_columns": ("ED_VAL",),
        "enhanced_variables": ("educational_assistance",),
    },
    {
        "key": "financial_assistance",
        "label": "Financial assistance",
        "raw_columns": ("FIN_VAL",),
        "enhanced_variables": ("financial_assistance",),
    },
    {
        "key": "survivor_benefits",
        "label": "Survivor benefits",
        "raw_columns": ("SRVS_VAL",),
        "enhanced_variables": ("survivor_benefits",),
    },
    {
        "key": "veterans_benefits",
        "label": "Veterans benefits",
        "raw_columns": ("VET_VAL",),
        "enhanced_variables": ("veterans_benefits",),
    },
    {
        "key": "workers_compensation",
        "label": "Workers' compensation",
        "raw_columns": ("WC_VAL",),
        "enhanced_variables": ("workers_compensation",),
    },
)

ADMIN_CALIBRATION_TARGETS: tuple[dict[str, Any], ...] = (
    {
        "element": "Child support received and paid",
        "variables": [
            "child_support_received",
            "child_support_expense",
            "net_child_support",
        ],
        "source": "OCSS FY 2024 Preliminary Data Report and Tables",
        "target": (
            "Use one gross-flow target for received and paid child support, "
            "then keep net child support as received minus paid."
        ),
        "implementation_note": (
            "OCSS administrative totals are the best timely state-level "
            "source, but they mostly cover child-support-program collections "
            "and state disbursement-unit flows, not all private informal "
            "payments."
        ),
    },
    {
        "element": "Energy assistance",
        "variables": ["spm_unit_energy_subsidy"],
        "source": "Census SPM technical documentation and HHS LIHEAP FY2024 profile",
        "target": (
            "Target LIHEAP-style energy assistance by state, including "
            "heating, cooling, crisis, and weatherization/home-repair "
            "components where the benefit is part of SPM resources."
        ),
        "implementation_note": (
            "Census says energy assistance includes LIHEAP or similar "
            "state/local programs, not LIHEAP alone."
        ),
    },
    {
        "element": "Utility assistance",
        "variables": ["spm_unit_energy_subsidy", "acp", "ebb"],
        "source": "Census Table B-6 footnote, Census SPM tech doc, USAC ACP data",
        "target": (
            "Use energy assistance plus ACP/EBB internet assistance. ACP "
            "should be part-year in 2024 because the federal program ended in "
            "June."
        ),
        "implementation_note": (
            "Current PE 2024 data has ACP/EBB at zero, so utility assistance "
            "equals energy assistance until broadband benefits are populated."
        ),
    },
    {
        "element": "Workers' compensation",
        "variables": ["workers_compensation"],
        "source": "NASI 2022 state summaries, uprated with NCCI indemnity severity",
        "target": (
            "Use NASI cash benefits by state: total benefits times one minus "
            "medical-benefit share."
        ),
        "implementation_note": (
            "A reasonable first 2022-to-2024 uprating factor is 1.05 * 1.06 = "
            "1.113, using NCCI rounded indemnity severity growth for 2023 and "
            "2024. Use state-specific NCCI severity if we need more precision."
        ),
    },
)


def _round_rate_set(rates: dict[str, float], digits: int = 4) -> dict[str, float]:
    return {group: round(value, digits) for group, value in rates.items()}


def _age_masks(age: MicroSeries) -> dict[str, Any]:
    return {
        "all": age >= 0,
        "child": age < 18,
        "working_age": (age >= 18) & (age < 65),
        "senior": age >= 65,
    }


def threshold_ratio_distribution(
    net_income: MicroSeries,
    threshold: MicroSeries,
    age: MicroSeries,
) -> dict[str, dict[str, float]]:
    """Return weighted person shares by SPM income/resource-to-threshold bin."""
    ratio = net_income / threshold
    age_masks = _age_masks(age)
    distributions: dict[str, dict[str, float]] = {}

    for group in AGE_GROUPS:
        group_mask = age_masks[group]
        distributions[group] = {}
        for key, _label, lower, upper in THRESHOLD_RATIO_BINS:
            if lower is None:
                bin_mask = ratio < upper
            elif upper is None:
                bin_mask = ratio >= lower
            else:
                bin_mask = (ratio >= lower) & (ratio < upper)
            distributions[group][key] = float(bin_mask[group_mask].mean())

    return distributions


def _rate_check(label: str, poverty_status: Any, age: MicroSeries, note: str) -> dict:
    return {
        "label": label,
        **_round_rate_set(poverty_rates(poverty_status, age)),
        "note": note,
    }


def _resource_means(sim: Any, year: int) -> dict[str, int | str]:
    means: dict[str, int | str] = {}
    for variable in RESOURCE_MEAN_VARIABLES:
        try:
            value = sim.calculate(variable, period=year, map_to="person")
        except Exception as error:
            means[variable] = f"{type(error).__name__}: {error}"
            continue
        means[variable] = round(float(value.mean()))
    means["note"] = "Weighted person-average values after mapping variables to people."
    return means


def _default_microsimulation_factory(dataset_path: str) -> Any:
    from policyengine_us import Microsimulation

    return Microsimulation(dataset=dataset_path)


def _missing_negative_income_source(
    *,
    key: str,
    label: str,
    dataset_path: str,
    note: str,
    error: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "key": key,
        "label": label,
        "dataset_path": dataset_path,
        "available": False,
        "income_variable": None,
        "person_count": None,
        "negative_person_count": None,
        "negative_person_share": None,
        "spm_unit_count": None,
        "negative_spm_unit_count": None,
        "negative_spm_unit_share": None,
        "negative_income_mass": None,
        "negative_income_abs_mass": None,
        "mean_spm_unit_income": None,
        "mean_negative_spm_unit_income": None,
        "minimum_spm_unit_income": None,
        "note": note,
    }
    if error:
        result["error"] = error
    return result


def _first_available_income_series(
    sim: Any,
    year: int,
    candidates: tuple[str, ...],
) -> tuple[str, MicroSeries, MicroSeries]:
    errors: list[str] = []
    for variable in candidates:
        try:
            spm_unit_income = sim.calculate(variable, period=year, map_to="spm_unit")
            person_income = sim.calculate(variable, period=year, map_to="person")
            return variable, spm_unit_income, person_income
        except Exception as error:
            errors.append(f"{variable}: {type(error).__name__}: {error}")

    raise RuntimeError("; ".join(errors))


def _negative_income_source_summary(
    *,
    key: str,
    label: str,
    dataset_path: str,
    sim: Any,
    year: int,
    candidates: tuple[str, ...],
) -> dict[str, Any]:
    try:
        income_variable, spm_unit_income, person_income = (
            _first_available_income_series(sim, year, candidates)
        )
    except Exception as error:
        return _missing_negative_income_source(
            key=key,
            label=label,
            dataset_path=dataset_path,
            note=(
                "No candidate SPM-unit income/resource variable could be "
                "calculated for this source."
            ),
            error=f"{type(error).__name__}: {error}",
        )

    negative_spm_unit = spm_unit_income < 0
    negative_person = person_income < 0
    valid_spm_unit = spm_unit_income == spm_unit_income
    valid_person = person_income == person_income
    negative_spm_unit_income = spm_unit_income[negative_spm_unit]
    negative_spm_unit_count = float(negative_spm_unit.sum())
    negative_income_mass = float(negative_spm_unit_income.sum())

    return {
        "key": key,
        "label": label,
        "dataset_path": dataset_path,
        "available": True,
        "income_variable": income_variable,
        "person_count": float(valid_person.sum()),
        "negative_person_count": float(negative_person.sum()),
        "negative_person_share": float(negative_person.mean()),
        "spm_unit_count": float(valid_spm_unit.sum()),
        "negative_spm_unit_count": negative_spm_unit_count,
        "negative_spm_unit_share": float(negative_spm_unit.mean()),
        "negative_income_mass": negative_income_mass,
        "negative_income_abs_mass": -negative_income_mass,
        "mean_spm_unit_income": float(spm_unit_income.mean()),
        "mean_negative_spm_unit_income": (
            float(negative_spm_unit_income.mean()) if negative_spm_unit_count else None
        ),
        "minimum_spm_unit_income": float(spm_unit_income.min()),
        "note": (
            "Prevalence is weighted after mapping the SPM-unit resource "
            "measure to people; mass is the weighted SPM-unit sum of negative "
            "income/resources."
        ),
    }


def _negative_income_comparison(
    enhanced: dict[str, Any],
    raw: dict[str, Any],
) -> dict[str, Any]:
    if not enhanced["available"] or not raw["available"]:
        unavailable = [
            source["label"] for source in (enhanced, raw) if not source["available"]
        ]
        return {
            "available": False,
            "note": (
                "Comparison requires both ECPS and raw CPS ASEC to load. "
                f"Unavailable source(s): {', '.join(unavailable)}."
            ),
            "negative_person_share_difference": None,
            "negative_person_count_difference": None,
            "negative_income_abs_mass_difference": None,
            "negative_income_abs_mass_ratio": None,
        }

    raw_mass = raw["negative_income_abs_mass"]
    return {
        "available": True,
        "note": "Differences are ECPS minus raw CPS ASEC.",
        "negative_person_share_difference": (
            enhanced["negative_person_share"] - raw["negative_person_share"]
        ),
        "negative_person_count_difference": (
            enhanced["negative_person_count"] - raw["negative_person_count"]
        ),
        "negative_income_abs_mass_difference": (
            enhanced["negative_income_abs_mass"] - raw["negative_income_abs_mass"]
        ),
        "negative_income_abs_mass_ratio": (
            enhanced["negative_income_abs_mass"] / raw_mass if raw_mass else None
        ),
    }


def compute_negative_income_diagnostics(
    *,
    year: int,
    enhanced_sim: Any,
    enhanced_dataset_path: str,
    raw_dataset_path: str = RAW_CPS_ASEC_2024,
    simulation_factory: Callable[[str], Any] = _default_microsimulation_factory,
) -> dict[str, Any]:
    """Compare negative SPM income/resource tails in ECPS and raw CPS ASEC."""
    enhanced = _negative_income_source_summary(
        key="enhanced_cps",
        label="Enhanced CPS (ECPS)",
        dataset_path=enhanced_dataset_path,
        sim=enhanced_sim,
        year=year,
        candidates=ENHANCED_NEGATIVE_INCOME_VARIABLE_CANDIDATES,
    )

    try:
        raw_sim = simulation_factory(raw_dataset_path)
    except Exception as error:
        raw = _missing_negative_income_source(
            key="raw_cps_asec",
            label="Raw CPS ASEC",
            dataset_path=raw_dataset_path,
            note=(
                "Raw CPS ASEC is present in the PolicyEngine US data "
                "repository as cps_2024.h5, but it was not loadable through "
                "policyengine_us.Microsimulation in this environment."
            ),
            error=f"{type(error).__name__}: {error}",
        )
    else:
        raw = _negative_income_source_summary(
            key="raw_cps_asec",
            label="Raw CPS ASEC",
            dataset_path=raw_dataset_path,
            sim=raw_sim,
            year=year,
            candidates=RAW_NEGATIVE_INCOME_VARIABLE_CANDIDATES,
        )

    return {
        "title": "Negative income tail diagnostic",
        "year": year,
        "income_variable_candidates": {
            "enhanced_cps": list(ENHANCED_NEGATIVE_INCOME_VARIABLE_CANDIDATES),
            "raw_cps_asec": list(RAW_NEGATIVE_INCOME_VARIABLE_CANDIDATES),
        },
        "sources": {
            "enhanced_cps": enhanced,
            "raw_cps_asec": raw,
        },
        "comparison": _negative_income_comparison(enhanced, raw),
        "note": (
            "This is a data-source diagnostic for whether negative SPM "
            "income/resource tail behavior may contribute to the Census/PE "
            "SPM rate gap."
        ),
    }


def _missing_source_replication(
    *,
    key: str,
    label: str,
    dataset_path: str,
    resource_variable: str,
    note: str,
    error: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "key": key,
        "label": label,
        "dataset_path": dataset_path,
        "available": False,
        "resource_variable": resource_variable,
        "threshold_variable": "spm_unit_spm_threshold",
        "rates": None,
        "population": None,
        "mean_resource": None,
        "median_resource": None,
        "mean_threshold": None,
        "threshold_ratio_distribution": None,
        "note": note,
    }
    if error:
        result["error"] = error
    return result


def _source_replication_summary(
    *,
    key: str,
    label: str,
    dataset_path: str,
    sim: Any,
    year: int,
    resource_variable: str,
    note: str,
) -> dict[str, Any]:
    try:
        age = sim.calculate("age", period=year)
        resource = sim.calculate(resource_variable, period=year, map_to="person")
        threshold = sim.calculate(
            "spm_unit_spm_threshold",
            period=year,
            map_to="person",
        )
    except Exception as error:
        return _missing_source_replication(
            key=key,
            label=label,
            dataset_path=dataset_path,
            resource_variable=resource_variable,
            note=note,
            error=f"{type(error).__name__}: {error}",
        )

    return {
        "key": key,
        "label": label,
        "dataset_path": dataset_path,
        "available": True,
        "resource_variable": resource_variable,
        "threshold_variable": "spm_unit_spm_threshold",
        "rates": _round_rate_set(poverty_rates(resource < threshold, age)),
        "population": float((age >= 0).sum()),
        "mean_resource": round(float(resource.mean())),
        "median_resource": round(float(resource.quantile(0.5))),
        "mean_threshold": round(float(threshold.mean())),
        "threshold_ratio_distribution": threshold_ratio_distribution(
            resource,
            threshold,
            age,
        ),
        "note": note,
    }


def _component_mean_gaps(
    *,
    enhanced_sim: Any,
    raw_sim: Any,
    year: int,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for variable, label in SOURCE_REPLICATION_COMPONENTS:
        try:
            enhanced = enhanced_sim.calculate(variable, period=year, map_to="person")
            raw = raw_sim.calculate(variable, period=year, map_to="person")
        except Exception as error:
            gaps.append(
                {
                    "variable": variable,
                    "label": label,
                    "available": False,
                    "enhanced_mean": None,
                    "raw_mean": None,
                    "difference": None,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            continue

        enhanced_mean = round(float(enhanced.mean()))
        raw_mean = round(float(raw.mean()))
        gaps.append(
            {
                "variable": variable,
                "label": label,
                "available": True,
                "enhanced_mean": enhanced_mean,
                "raw_mean": raw_mean,
                "difference": enhanced_mean - raw_mean,
            }
        )

    return sorted(
        gaps,
        key=lambda row: abs(row["difference"] or 0),
        reverse=True,
    )


def _raw_asec_zip_path() -> Path:
    configured = os.environ.get("POVERTY_DASHBOARD_ASEC_ZIP")
    if configured:
        return Path(configured)

    path = Path(tempfile.gettempdir()) / "asecpub25csv.zip"
    if not path.exists():
        urllib.request.urlretrieve(CENSUS_ASEC_2024_ZIP, path)
    return path


def _raw_asec_person_frame(zip_path: str | Path | None = None) -> pd.DataFrame:
    leaf_columns = {
        column
        for component in CPS_TOTAL_INCOME_LEAF_COMPONENTS
        for column in component["raw_columns"]
    }
    usecols = [
        "SPM_ID",
        "A_FNLWGT",
        "PTOTVAL",
        "SPM_TOTVAL",
        "SPM_WEIGHT",
        *sorted(leaf_columns),
    ]
    path = Path(zip_path) if zip_path is not None else _raw_asec_zip_path()
    with ZipFile(path) as archive:
        with archive.open(CENSUS_ASEC_2024_PERSON_FILE) as file:
            return pd.read_csv(file, usecols=usecols).fillna(0)


def _weighted_mean(values: Any, weights: Any) -> float:
    return float(MicroSeries(values, weights=weights).mean())


def _reconstruction_metrics(values: Any, target: Any, weights: Any) -> dict[str, Any]:
    residual = pd.Series(values).to_numpy(dtype=float) - pd.Series(target).to_numpy(
        dtype=float
    )
    abs_residual = abs(residual)
    return {
        "mean_abs_error": float(abs_residual.mean()),
        "max_abs_error": float(abs_residual.max()),
        "exact_share": float((abs_residual < 0.5).mean()),
        "weighted_mean_abs_error": _weighted_mean(abs_residual, weights),
        "weighted_mean_error": _weighted_mean(residual, weights),
    }


def _enhanced_total_income_leaf_mean(
    sim: Any,
    variables: tuple[str, ...] | None,
    year: int,
) -> tuple[float | None, str | None]:
    if variables is None:
        return None, "No one-to-one PolicyEngine variable for this CPS leaf."

    total = None
    try:
        for variable in variables:
            values = sim.calculate(variable, period=year, map_to="person")
            total = values if total is None else total + values
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"

    if total is None:
        return None, "No PolicyEngine variables configured."
    return round(float(total.mean())), None


def compute_total_income_leaf_diagnostics(
    *,
    year: int,
    enhanced_sim: Any,
    raw_asec_zip_path: str | Path | None = None,
) -> dict[str, Any]:
    """Reconstruct Census SPM_TOTVAL from raw ASEC income leaves."""
    if year != 2024:
        raise ValueError("Raw ASEC total-income diagnostics are pinned to 2024.")

    person = _raw_asec_person_frame(raw_asec_zip_path)
    leaf_columns = [
        column
        for component in CPS_TOTAL_INCOME_LEAF_COMPONENTS
        for column in component["raw_columns"]
    ]
    leaf_sum = person[leaf_columns].sum(axis=1)
    unit = (
        pd.DataFrame(
            {
                "leaf_income": leaf_sum,
                "ptotval": person["PTOTVAL"],
                "spm_totval": person["SPM_TOTVAL"],
                "spm_weight": person["SPM_WEIGHT"],
                "spm_id": person["SPM_ID"],
            }
        )
        .groupby("spm_id", sort=False)
        .agg(
            leaf_income=("leaf_income", "sum"),
            ptotval=("ptotval", "sum"),
            spm_totval=("spm_totval", "first"),
            spm_weight=("spm_weight", "first"),
        )
    )

    components: list[dict[str, Any]] = []
    for component in CPS_TOTAL_INCOME_LEAF_COMPONENTS:
        raw_values = person[list(component["raw_columns"])].sum(axis=1)
        raw_mean = round(_weighted_mean(raw_values, person["A_FNLWGT"]))
        enhanced_mean, error = _enhanced_total_income_leaf_mean(
            enhanced_sim,
            component["enhanced_variables"],
            year,
        )
        components.append(
            {
                "key": component["key"],
                "label": component["label"],
                "raw_columns": list(component["raw_columns"]),
                "enhanced_variables": (
                    list(component["enhanced_variables"])
                    if component["enhanced_variables"] is not None
                    else []
                ),
                "raw_mean": raw_mean,
                "enhanced_mean": enhanced_mean,
                "difference": (
                    enhanced_mean - raw_mean if enhanced_mean is not None else None
                ),
                "enhanced_available": enhanced_mean is not None,
                "note": error,
            }
        )

    components.sort(
        key=lambda row: abs(row["difference"] or row["raw_mean"] or 0),
        reverse=True,
    )

    return {
        "title": "Raw ASEC SPM total-income reconstruction",
        "year": year,
        "source_url": CENSUS_ASEC_2024_ZIP,
        "raw_person_file": CENSUS_ASEC_2024_PERSON_FILE,
        "leaf_columns": leaf_columns,
        "ptotval_from_person_leaves": _reconstruction_metrics(
            leaf_sum,
            person["PTOTVAL"],
            person["A_FNLWGT"],
        ),
        "spm_totval_from_ptotval": _reconstruction_metrics(
            unit["ptotval"],
            unit["spm_totval"],
            unit["spm_weight"],
        ),
        "spm_totval_from_person_leaves": _reconstruction_metrics(
            unit["leaf_income"],
            unit["spm_totval"],
            unit["spm_weight"],
        ),
        "component_mean_gaps": components,
        "note": (
            "Census SPM_TOTVAL is the SPM-unit sum of person PTOTVAL. "
            "PTOTVAL is reconstructed from public-use person income leaves; "
            "capital gains, noncash benefits, refundable credits, taxes, and "
            "SPM expenses are not part of SPM_TOTVAL."
        ),
    }


def compute_source_replication_diagnostics(
    *,
    year: int,
    enhanced_sim: Any,
    enhanced_dataset_path: str,
    raw_dataset_path: str = RAW_CPS_ASEC_2024,
    simulation_factory: Callable[[str], Any] = _default_microsimulation_factory,
) -> dict[str, Any]:
    """Compare ECPS modeled resources with a raw CPS reported-resource control."""
    enhanced = _source_replication_summary(
        key="enhanced_cps",
        label="Enhanced CPS (ECPS)",
        dataset_path=enhanced_dataset_path,
        sim=enhanced_sim,
        year=year,
        resource_variable="spm_unit_net_income",
        note="Uses PolicyEngine-modeled SPM resources on the enhanced CPS.",
    )

    raw_sim = None
    try:
        raw_sim = simulation_factory(raw_dataset_path)
    except Exception as error:
        raw = _missing_source_replication(
            key="raw_cps_asec",
            label="Raw CPS ASEC",
            dataset_path=raw_dataset_path,
            resource_variable="spm_unit_net_income_reported",
            note=(
                "Raw CPS ASEC could not be loaded for the validation-only "
                "reported-resource replication."
            ),
            error=f"{type(error).__name__}: {error}",
        )
    else:
        raw = _source_replication_summary(
            key="raw_cps_asec",
            label="Raw CPS ASEC",
            dataset_path=raw_dataset_path,
            sim=raw_sim,
            year=year,
            resource_variable="spm_unit_net_income_reported",
            note=(
                "Uses Census-reported SPM resources as a validation-only "
                "control, not as an ECPS pipeline input."
            ),
        )

    return {
        "title": "Raw CPS replication control",
        "year": year,
        "sources": {
            "enhanced_cps": enhanced,
            "raw_cps_asec": raw,
        },
        "component_mean_gaps": (
            _component_mean_gaps(
                enhanced_sim=enhanced_sim,
                raw_sim=raw_sim,
                year=year,
            )
            if raw_sim is not None
            else []
        ),
        "note": (
            "If raw CPS ASEC with reported SPM resources is close to Census "
            "but ECPS modeled resources are not, the gap is more likely in "
            "the enhanced CPS income distribution, calibration, or imputation "
            "than in individual SPM program rows."
        ),
    }


def _census_2024_report(path: Path = DATA_CENSUS_SPM_2024) -> dict[str, Any]:
    with path.open() as file:
        return json.load(file)


def compute_spm_gap_diagnostics(
    region_code: str = "us",
    year: int = 2024,
    census_report_path: Path = DATA_CENSUS_SPM_2024,
) -> dict[str, Any]:
    """Compute Census/PolicyEngine SPM diagnostics for the dashboard."""
    from policyengine_us import Microsimulation

    if year != 2024:
        raise ValueError(
            "SPM report diagnostics currently compare against Census 2024."
        )

    census = _census_2024_report(census_report_path)
    dataset_path = resolve_dataset(region_code)
    sim = Microsimulation(dataset=dataset_path)
    age = sim.calculate("age", period=year)
    net_income = sim.calculate("spm_unit_net_income", period=year, map_to="person")
    threshold = sim.calculate("spm_unit_spm_threshold", period=year, map_to="person")
    omitted_additions = spm_unit_component_as_person(
        sim=sim,
        variables=("child_support_received", "workers_compensation"),
        year=year,
        person_reference=age,
    )
    if omitted_additions is None:
        raise RuntimeError("Expected omitted SPM additions were not available.")
    corrected_net_income = net_income + omitted_additions

    person_in_poverty = sim.calculate("person_in_poverty", period=year)
    in_poverty = sim.calculate("in_poverty", period=year, map_to="person")
    spm_unit_poverty = sim.calculate(
        "spm_unit_is_in_spm_poverty",
        period=year,
        map_to="person",
    )

    checks = [
        _rate_check(
            "person_in_poverty",
            person_in_poverty,
            age,
            "Person-level wrapper around the SPM-unit poverty variable.",
        ),
        _rate_check(
            "in_poverty mapped to person",
            in_poverty,
            age,
            "SPM-unit poverty variable projected to people.",
        ),
        _rate_check(
            "spm_unit_is_in_spm_poverty mapped to person",
            spm_unit_poverty,
            age,
            "Explicit test of spm_unit_net_income < spm_unit_spm_threshold.",
        ),
        _rate_check(
            "modeled net income plus omitted SPM additions",
            corrected_net_income < threshold,
            age,
            "Adds child support received and workers' compensation without "
            "rerunning the microsimulation.",
        ),
    ]

    census_distribution = census["threshold_ratio_distribution"]["spm_2024"]
    modeled_distribution = threshold_ratio_distribution(net_income, threshold, age)
    corrected_distribution = threshold_ratio_distribution(
        corrected_net_income,
        threshold,
        age,
    )
    source_replication = compute_source_replication_diagnostics(
        year=year,
        enhanced_sim=sim,
        enhanced_dataset_path=dataset_path,
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "title": "Why is PolicyEngine higher than Census SPM?",
        "summary": [
            (
                "PolicyEngine's 2024 SPM-like rate is much higher than "
                "Census's 2024 SPM rate."
            ),
            (
                "Adding child support received and workers' compensation to PE "
                "SPM resources closes only a small share of the gap."
            ),
            (
                "Raw CPS ASEC with Census-reported SPM resources can closely "
                "replicate the Census report, so PolicyEngine's SPM threshold "
                "formula is not the main driver."
            ),
            (
                "The Table B-5 threshold-ratio distribution shows PE has much "
                "more mass below the poverty line than Census, pointing toward "
                "the enhanced CPS income distribution, reweighting, universe, "
                "and threshold pipeline."
            ),
            (
                "Census SPM resource aggregates are validation controls, not "
                "inputs for ECPS construction or clone imputation."
            ),
        ],
        "benchmarks": {
            "census_2024_spm": census["national"],
            "census_2024_spm_deep": {
                "all": census_distribution["all"]["less_than_0_50"],
                "child": census_distribution["child"]["less_than_0_50"],
                "working_age": census_distribution["working_age"]["less_than_0_50"],
                "senior": census_distribution["senior"]["less_than_0_50"],
                "source": "Census Table B-5, SPM, Less than 0.50 threshold ratio",
            },
            "policyengine_2026_committed": {
                "all": 0.21903239157830484,
                "child": 0.21751115956910017,
                "working_age": 0.2388378199508652,
                "senior": 0.1543611070024721,
                "deep_all": 0.07862131650456361,
                "deep_child": 0.05454291800770483,
                "people": 341815362.3148309,
            },
        },
        "policyengine_2024_checks": checks,
        "policyengine_2024_element_effects": compute_spm_element_effects(
            region_code,
            year=year,
        ),
        "admin_calibration_targets": list(ADMIN_CALIBRATION_TARGETS),
        "threshold_ratio_distribution": {
            "bins": [
                {"key": key, "label": label}
                for key, label, _lower, _upper in THRESHOLD_RATIO_BINS
            ],
            "census_2024_spm": census_distribution,
            "policyengine_2024_modeled": modeled_distribution,
            "policyengine_2024_modeled_plus_omitted_resources": (
                corrected_distribution
            ),
        },
        "source_replication_diagnostics": source_replication,
        "total_income_leaf_diagnostics": compute_total_income_leaf_diagnostics(
            year=year,
            enhanced_sim=sim,
        ),
        "negative_income_diagnostics": compute_negative_income_diagnostics(
            year=year,
            enhanced_sim=sim,
            enhanced_dataset_path=dataset_path,
        ),
        "policyengine_2024_resource_means": _resource_means(sim, year),
        "bls_2024_reference_thresholds": {
            "two_adults_two_children": {
                "renter": 39430,
                "owner_with_mortgage": 39068,
                "owner_without_mortgage": 32586,
                "official_threshold": 31812,
            },
            "note": (
                "BLS finalized 2024 research SPM thresholds on April 23, 2025. "
                "Census combines SPM thresholds with SPM resources to produce "
                "SPM poverty statistics."
            ),
        },
        "sources": {
            "tables_page": TABLES_PAGE,
            "table_b2": TABLE_B2,
            "table_b5": TABLE_B5,
            "table_b6": TABLE_B6,
            "state_3yr": census["sources"]["state_3yr"],
            "bls_2024_thresholds": BLS_2024_THRESHOLDS,
            "census_tax_model": CENSUS_TAX_MODEL,
            "census_spm_techdoc": CENSUS_SPM_TECHDOC,
            "ocss_2024_preliminary": OCSS_2024_PRELIMINARY,
            "liheap_2024_profile": LIHEAP_2024_PROFILE,
            "nasi_workers_comp_2022": NASI_WORKERS_COMP_2022,
            "ncci_2024_state_of_the_line": NCCI_2024_SOTL,
            "ncci_2025_state_of_the_line": NCCI_2025_SOTL,
        },
    }


def main() -> None:
    """Run the SPM gap diagnostics calculation CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("region", nargs="?", default="us")
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--out", default=str(DEFAULT_DIAGNOSTICS))
    args = parser.parse_args()

    payload = compute_spm_gap_diagnostics(args.region, year=args.year)
    output = json.dumps(payload, indent=2) + "\n"
    if args.out == "-":
        sys.stdout.write(output)
    else:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
