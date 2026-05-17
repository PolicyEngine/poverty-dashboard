"""Arithmetic SPM element effects for PolicyEngine poverty diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Literal

from microdf import MicroSeries

from poverty_dashboard.poverty_calc import YEAR, resolve_dataset

AgeGroup = Literal["all", "child", "working_age", "senior"]
ElementSection = Literal["addition", "subtraction"]

AGE_GROUPS: tuple[AgeGroup, ...] = ("all", "child", "working_age", "senior")


@dataclass(frozen=True)
class SpmElement:
    """A Census SPM element and its PolicyEngine variable mapping."""

    label: str
    section: ElementSection
    variables: tuple[str, ...]
    note: str = ""
    included_in_policyengine_net_income: bool = True


SPM_ELEMENTS: tuple[SpmElement, ...] = (
    SpmElement("Social Security", "addition", ("social_security",)),
    SpmElement(
        "Refundable tax credits",
        "addition",
        ("eitc", "refundable_ctc"),
        "Census combines the federal EITC and refundable CTC in this Table B-6 row.",
    ),
    SpmElement("SNAP", "addition", ("snap",)),
    SpmElement("SSI", "addition", ("ssi",)),
    SpmElement("Refundable Child Tax Credit", "addition", ("refundable_ctc",)),
    SpmElement(
        "Housing subsidies",
        "addition",
        ("spm_unit_capped_housing_subsidy",),
    ),
    SpmElement(
        "School lunch",
        "addition",
        ("free_school_meals", "reduced_price_school_meals"),
    ),
    SpmElement(
        "Child support received",
        "addition",
        ("child_support_received",),
        "PolicyEngine input exists but is not yet included in PE SPM net income.",
        False,
    ),
    SpmElement("Unemployment insurance", "addition", ("unemployment_compensation",)),
    SpmElement("TANF/general assistance", "addition", ("tanf",)),
    SpmElement("WIC", "addition", ("wic",)),
    SpmElement(
        "Utility assistance",
        "addition",
        ("spm_unit_energy_subsidy", "acp", "ebb"),
        "Census Table B-6 defines utility assistance as ACP plus other "
        "noncash energy benefits; PolicyEngine currently has zero ACP/EBB in "
        "the 2024 data.",
    ),
    SpmElement(
        "Energy assistance",
        "addition",
        ("spm_unit_energy_subsidy",),
        "PolicyEngine's 2024 energy subsidy input is very small relative to "
        "the Census Table B-6 effect.",
    ),
    SpmElement(
        "Workers' compensation",
        "addition",
        ("workers_compensation",),
        "PolicyEngine input exists but is not yet included in PE SPM net income.",
        False,
    ),
    SpmElement(
        "Broadband Assistance",
        "addition",
        ("acp", "ebb"),
        "PolicyEngine includes ACP and EBB in SPM net income when present.",
    ),
    SpmElement(
        "State refundable tax credits",
        "addition",
        ("state_refundable_credits",),
        "PolicyEngine-only diagnostic; Census Table B-6 does not publish a "
        "state refundable tax credit effect.",
    ),
    SpmElement("Child support paid", "subtraction", ("child_support_expense",)),
    SpmElement(
        "Federal income tax",
        "subtraction",
        ("income_tax_before_refundable_credits",),
        "Uses pre-refundable-credit tax because Census reports refundable "
        "credits separately.",
    ),
    SpmElement(
        "State income tax before refundable credits",
        "subtraction",
        ("state_income_tax_before_refundable_credits",),
        "PolicyEngine-only diagnostic; Census Table B-6 does not publish a "
        "state income tax effect.",
    ),
    SpmElement(
        "Work expenses",
        "subtraction",
        ("spm_unit_capped_work_childcare_expenses",),
    ),
    SpmElement("FICA", "subtraction", ("spm_unit_payroll_tax",)),
    SpmElement(
        "Medical expenses",
        "subtraction",
        ("spm_unit_medical_out_of_pocket_expenses",),
    ),
)


def poverty_rates(poverty_status: Any, age: MicroSeries) -> dict[AgeGroup, float]:
    """Return weighted person-level poverty rates by age group."""
    is_child = age < 18
    is_working_age = (age >= 18) & (age < 65)
    is_senior = age >= 65

    return {
        "all": float(poverty_status.mean()),
        "child": float(poverty_status[is_child].mean()),
        "working_age": float(poverty_status[is_working_age].mean()),
        "senior": float(poverty_status[is_senior].mean()),
    }


def poverty_effect_from_component(
    net_income: MicroSeries,
    threshold: MicroSeries,
    component: MicroSeries,
    age: MicroSeries,
    section: ElementSection,
    included_in_net_income: bool = True,
) -> dict[AgeGroup, float]:
    """Calculate the arithmetic poverty effect of removing one SPM element.

    This mirrors Census Table B-6's sign convention:
    additions usually have negative effects because removing the resource raises
    poverty, while subtractions usually have positive effects because removing
    the subtraction raises resources and lowers poverty. It does not rerun the
    tax-benefit model or allow behavioral/eligibility interactions.

    If PolicyEngine has the component input but the current SPM net-income
    formula omits it, first add it to the baseline resource definition so the
    displayed effect reflects the upstream fix needed to match Census.
    """
    if section == "addition" and not included_in_net_income:
        baseline_income = net_income + component
        counterfactual_income = net_income
    elif section == "subtraction" and not included_in_net_income:
        baseline_income = net_income - component
        counterfactual_income = net_income
    elif section == "addition":
        baseline_income = net_income
        counterfactual_income = net_income - component
    else:
        baseline_income = net_income
        counterfactual_income = net_income + component

    baseline_poverty = baseline_income < threshold
    counterfactual_poverty = counterfactual_income < threshold
    baseline_rates = poverty_rates(baseline_poverty, age)
    counterfactual_rates = poverty_rates(counterfactual_poverty, age)
    return {
        group: baseline_rates[group] - counterfactual_rates[group]
        for group in AGE_GROUPS
    }


def _spm_unit_series_to_person(
    sim: Any,
    spm_unit_values: MicroSeries,
    person_reference: MicroSeries,
) -> MicroSeries:
    person_values = sim.map_result(
        spm_unit_values.array,
        source_entity="spm_unit",
        target_entity="person",
    )
    return MicroSeries(person_values, weights=person_reference.weights)


def spm_unit_component_as_person(
    sim: Any,
    variables: tuple[str, ...],
    year: int,
    person_reference: MicroSeries,
) -> MicroSeries | None:
    """Return SPM-unit total component amounts projected to people."""
    if not variables:
        return None

    component = None
    for variable in variables:
        spm_unit_values = sim.calculate(variable, period=year, map_to="spm_unit")
        component = (
            spm_unit_values if component is None else component + spm_unit_values
        )

    if component is None:
        return None

    return _spm_unit_series_to_person(
        sim=sim,
        spm_unit_values=component,
        person_reference=person_reference,
    )


def compute_spm_element_effects(
    region_code: str = "us",
    year: int = YEAR,
) -> list[dict[str, Any]]:
    """Compute PolicyEngine SPM element effects without rerunning microsimulation."""
    from policyengine_us import Microsimulation

    sim = Microsimulation(dataset=resolve_dataset(region_code))
    age = sim.calculate("age", period=year)
    net_income = sim.calculate("spm_unit_net_income", period=year, map_to="person")
    threshold = sim.calculate("spm_unit_spm_threshold", period=year, map_to="person")

    effects: list[dict[str, Any]] = []
    for element in SPM_ELEMENTS:
        component = spm_unit_component_as_person(
            sim=sim,
            variables=element.variables,
            year=year,
            person_reference=age,
        )
        if component is None:
            effects.append(
                {
                    "element": element.label,
                    "section": element.section,
                    "variables": list(element.variables),
                    "supported": False,
                    "note": element.note,
                    "included_in_policyengine_net_income": (
                        element.included_in_policyengine_net_income
                    ),
                    "all": None,
                    "child": None,
                    "working_age": None,
                    "senior": None,
                    "mean_amount": None,
                }
            )
            continue

        effects.append(
            {
                "element": element.label,
                "section": element.section,
                "variables": list(element.variables),
                "supported": True,
                "note": element.note,
                "included_in_policyengine_net_income": (
                    element.included_in_policyengine_net_income
                ),
                **poverty_effect_from_component(
                    net_income=net_income,
                    threshold=threshold,
                    component=component,
                    age=age,
                    section=element.section,
                    included_in_net_income=(
                        element.included_in_policyengine_net_income
                    ),
                ),
                "mean_amount": float(component.mean()),
            }
        )

    return effects


def main() -> None:
    """Run the SPM element effect calculation CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("region", nargs="?", default="us")
    parser.add_argument("--year", type=int, default=YEAR)
    args = parser.parse_args()

    payload = {
        "region_code": args.region,
        "year": args.year,
        "effects": compute_spm_element_effects(args.region, year=args.year),
    }
    json.dump(payload, fp=sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
