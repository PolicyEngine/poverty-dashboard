from __future__ import annotations

import pytest
from microdf import MicroSeries

from poverty_dashboard.spm_diagnostics import (
    compute_negative_income_diagnostics,
    compute_source_replication_diagnostics,
    compute_total_income_leaf_diagnostics,
)


class FakeSimulation:
    def __init__(
        self,
        *,
        spm_unit_income: list[int],
        spm_unit_weights: list[int],
        person_income: list[int],
        person_weights: list[int],
        reported_available: bool = True,
        age: list[int] | None = None,
        threshold: list[int] | None = None,
    ) -> None:
        self.spm_unit_income = spm_unit_income
        self.spm_unit_weights = spm_unit_weights
        self.person_income = person_income
        self.person_weights = person_weights
        self.reported_available = reported_available
        self.age = age or list(range(len(person_income)))
        self.threshold = threshold or [100] * len(person_income)

    def calculate(
        self,
        variable: str,
        period: int,
        map_to: str | None = None,
    ) -> MicroSeries:
        assert period == 2024
        assert map_to in {"person", "spm_unit", None}
        if variable == "age":
            assert map_to is None
            return MicroSeries(self.age, weights=self.person_weights)
        if variable == "spm_unit_spm_threshold":
            assert map_to == "person"
            return MicroSeries(self.threshold, weights=self.person_weights)
        if variable == "spm_unit_net_income_reported" and not self.reported_available:
            raise ValueError("reported income unavailable")
        if variable not in {
            "spm_unit_net_income_reported",
            "spm_unit_net_income",
            "spm_unit_market_income",
            "employment_income",
        }:
            raise ValueError(f"Unexpected variable: {variable}")
        if map_to == "spm_unit":
            return MicroSeries(self.spm_unit_income, weights=self.spm_unit_weights)
        return MicroSeries(self.person_income, weights=self.person_weights)


class FlexibleSimulation:
    def calculate(
        self,
        variable: str,
        period: int,
        map_to: str | None = None,
    ) -> MicroSeries:
        assert period == 2024
        assert map_to == "person"
        values = {
            "employment_income": [10, 20],
            "taxable_private_pension_income": [2, 0],
            "tax_exempt_private_pension_income": [1, 0],
            "taxable_public_pension_income": [0, 0],
            "tax_exempt_public_pension_income": [0, 0],
            "miscellaneous_income": [4, 0],
            "alimony_income": [1, 1],
            "strike_benefits": [0, 2],
            "educational_assistance": [1, 3],
            "financial_assistance": [2, 4],
            "survivor_benefits": [3, 5],
            "tanf": [0, 2],
        }.get(variable, [0, 0])
        return MicroSeries(values, weights=[1, 1])


def test__given_ecps_and_raw_cps_load__then_negative_income_metrics_are_compared():
    # Given
    enhanced_sim = FakeSimulation(
        spm_unit_income=[-100, 50],
        spm_unit_weights=[2, 3],
        person_income=[-100, 50, 50],
        person_weights=[2, 1, 2],
    )
    raw_sim = FakeSimulation(
        spm_unit_income=[-25, 100],
        spm_unit_weights=[4, 1],
        person_income=[-25, -25, 100],
        person_weights=[1, 3, 1],
    )

    # When
    result = compute_negative_income_diagnostics(
        year=2024,
        enhanced_sim=enhanced_sim,
        enhanced_dataset_path="hf://policyengine/policyengine-us-data/enhanced.h5",
        raw_dataset_path="hf://policyengine/policyengine-us-data/cps.h5",
        simulation_factory=lambda _path: raw_sim,
    )

    # Then
    enhanced = result["sources"]["enhanced_cps"]
    raw = result["sources"]["raw_cps_asec"]
    comparison = result["comparison"]
    assert enhanced["available"]
    assert raw["available"]
    assert enhanced["negative_person_share"] == pytest.approx(2 / 5)
    assert raw["negative_person_share"] == pytest.approx(4 / 5)
    assert enhanced["negative_income_mass"] == pytest.approx(-200)
    assert enhanced["negative_income_abs_mass"] == pytest.approx(200)
    assert raw["negative_income_abs_mass"] == pytest.approx(100)
    assert comparison["available"]
    assert comparison["negative_person_share_difference"] == pytest.approx(-2 / 5)
    assert comparison["negative_income_abs_mass_difference"] == pytest.approx(100)
    assert comparison["negative_income_abs_mass_ratio"] == pytest.approx(2)
    assert enhanced["income_variable"] == "spm_unit_net_income"
    assert raw["income_variable"] == "spm_unit_net_income_reported"


def test__given_reported_income_missing__then_modeled_income_candidate_is_used():
    # Given
    enhanced_sim = FakeSimulation(
        spm_unit_income=[-10, 20],
        spm_unit_weights=[1, 1],
        person_income=[-10, 20],
        person_weights=[1, 1],
        reported_available=False,
    )
    raw_sim = FakeSimulation(
        spm_unit_income=[-5, 15],
        spm_unit_weights=[1, 1],
        person_income=[-5, 15],
        person_weights=[1, 1],
        reported_available=False,
    )

    # When
    result = compute_negative_income_diagnostics(
        year=2024,
        enhanced_sim=enhanced_sim,
        enhanced_dataset_path="enhanced.h5",
        raw_dataset_path="raw.h5",
        simulation_factory=lambda _path: raw_sim,
    )

    # Then
    assert result["sources"]["enhanced_cps"]["income_variable"] == "spm_unit_net_income"
    assert result["sources"]["raw_cps_asec"]["income_variable"] == (
        "spm_unit_net_income"
    )


def test__given_raw_cps_reported_resources__then_source_replication_is_compared():
    # Given
    enhanced_sim = FakeSimulation(
        spm_unit_income=[90, 120],
        spm_unit_weights=[1, 3],
        person_income=[90, 120, 120],
        person_weights=[1, 1, 2],
        age=[10, 30, 70],
        threshold=[100, 100, 100],
    )
    raw_sim = FakeSimulation(
        spm_unit_income=[80, 150],
        spm_unit_weights=[2, 2],
        person_income=[80, 150, 150],
        person_weights=[1, 1, 2],
        age=[10, 30, 70],
        threshold=[100, 100, 100],
    )

    # When
    result = compute_source_replication_diagnostics(
        year=2024,
        enhanced_sim=enhanced_sim,
        enhanced_dataset_path="enhanced.h5",
        raw_dataset_path="raw.h5",
        simulation_factory=lambda _path: raw_sim,
    )

    # Then
    enhanced = result["sources"]["enhanced_cps"]
    raw = result["sources"]["raw_cps_asec"]
    assert enhanced["resource_variable"] == "spm_unit_net_income"
    assert raw["resource_variable"] == "spm_unit_net_income_reported"
    assert enhanced["rates"]["all"] == pytest.approx(1 / 4)
    assert raw["rates"]["all"] == pytest.approx(1 / 4)
    assert enhanced["resource_distribution"]["share_below_threshold"] == pytest.approx(
        1 / 4
    )
    assert raw["resource_distribution"]["resource_quantiles"]["p50"] == pytest.approx(
        150
    )
    assert raw["resource_distribution"]["threshold_ratio_quantiles"]["p10"] == (
        pytest.approx(0.8)
    )
    assert result["component_mean_gaps"][0]["available"]
    assert result["component_mean_gaps"][0]["below_threshold_difference"] == (
        pytest.approx(10)
    )


def test__given_raw_cps_not_loadable__then_availability_limitation_is_recorded():
    # Given
    enhanced_sim = FakeSimulation(
        spm_unit_income=[-100, 50],
        spm_unit_weights=[2, 3],
        person_income=[-100, 50, 50],
        person_weights=[2, 1, 2],
    )

    def failing_factory(_path: str) -> FakeSimulation:
        raise ValueError("raw CPS enum mismatch")

    # When
    result = compute_negative_income_diagnostics(
        year=2024,
        enhanced_sim=enhanced_sim,
        enhanced_dataset_path="enhanced.h5",
        raw_dataset_path="raw.h5",
        simulation_factory=failing_factory,
    )

    # Then
    raw = result["sources"]["raw_cps_asec"]
    comparison = result["comparison"]
    assert result["sources"]["enhanced_cps"]["available"]
    assert not raw["available"]
    assert raw["negative_person_share"] is None
    assert "not loadable" in raw["note"]
    assert "raw CPS enum mismatch" in raw["error"]
    assert not comparison["available"]
    assert comparison["negative_income_abs_mass_difference"] is None


def test__given_raw_asec_leaves__then_spm_totval_is_reconstructed(monkeypatch):
    # Given
    import pandas as pd

    raw = pd.DataFrame(
        {
            "SPM_ID": [1, 1, 2],
            "A_FNLWGT": [1, 2, 3],
            "SPM_WEIGHT": [3, 3, 3],
            "SPM_TOTVAL": [30, 30, 43],
            "SPM_RESOURCES": [27, 27, 44],
            "PTOTVAL": [10, 20, 43],
            "WSAL_VAL": [10, 20, 0],
            "PNSN_VAL": [0, 0, 3],
            "ANN_VAL": [0, 0, 4],
            "OI_VAL": [0, 0, 6],
            "ED_VAL": [0, 0, 8],
            "FIN_VAL": [0, 0, 10],
            "SRVS_VAL": [0, 0, 12],
        }
    )
    for column in [
        "CSP_VAL",
        "DBTN_VAL",
        "DIV_VAL",
        "DSAB_VAL",
        "FRSE_VAL",
        "INT_VAL",
        "PAW_VAL",
        "RNT_VAL",
        "SEMP_VAL",
        "SSI_VAL",
        "SS_VAL",
        "UC_VAL",
        "VET_VAL",
        "WC_VAL",
    ]:
        raw[column] = 0
    for column in [
        "SPM_ACTC",
        "SPM_BBSUBVAL",
        "SPM_CAPHOUSESUB",
        "SPM_CAPWKCCXPNS",
        "SPM_CHILDSUPPD",
        "SPM_EITC",
        "SPM_ENGVAL",
        "SPM_FEDTAXBC",
        "SPM_FICA",
        "SPM_MEDXPNS",
        "SPM_SCHLUNCH",
        "SPM_SNAPSUB",
        "SPM_STTAX",
        "SPM_WICVAL",
    ]:
        raw[column] = 0
    raw["SPM_EITC"] = [5, 5, 0]
    raw["SPM_FEDTAXBC"] = [8, 8, 0]
    raw["SPM_SNAPSUB"] = [0, 0, 2]
    raw["SPM_MEDXPNS"] = [0, 0, 1]

    monkeypatch.setattr(
        "poverty_dashboard.spm_diagnostics._raw_asec_person_frame",
        lambda _path=None: raw,
    )

    # When
    result = compute_total_income_leaf_diagnostics(
        year=2024,
        enhanced_sim=FlexibleSimulation(),
    )

    # Then
    assert result["spm_totval_from_person_leaves"]["exact_share"] == pytest.approx(1)
    assert result["spm_resource_formula"]["spm_resources_from_formula"][
        "exact_share"
    ] == pytest.approx(1)
    assert result["ptotval_from_person_leaves"]["max_abs_error"] == pytest.approx(0)
    refundable_credits = next(
        row
        for row in result["spm_resource_formula"]["components"]
        if row["key"] == "refundable_tax_credits"
    )
    assert refundable_credits["raw_mean"] == 3
    assert refundable_credits["enhanced_variables"] == ["eitc", "refundable_ctc"]
    pension = next(
        row for row in result["component_mean_gaps"] if row["key"] == "pension_income"
    )
    assert pension["raw_mean"] == 4
    assert pension["enhanced_mean"] == 2
    assert pension["enhanced_variables"] == [
        "taxable_private_pension_income",
        "tax_exempt_private_pension_income",
        "taxable_public_pension_income",
        "tax_exempt_public_pension_income",
    ]
    other = next(
        row for row in result["component_mean_gaps"] if row["key"] == "other_income"
    )
    assert other["enhanced_variables"] == [
        "miscellaneous_income",
        "alimony_income",
        "strike_benefits",
    ]
    assert other["raw_mean"] == 3
    assert other["enhanced_mean"] == 4
    education = next(
        row
        for row in result["component_mean_gaps"]
        if row["key"] == "education_assistance"
    )
    assert education["enhanced_variables"] == ["educational_assistance"]
    assert education["raw_mean"] == 4
    assert education["enhanced_mean"] == 2
