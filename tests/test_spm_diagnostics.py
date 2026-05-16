from __future__ import annotations

import pytest
from microdf import MicroSeries

from poverty_dashboard.spm_diagnostics import (
    compute_negative_income_diagnostics,
    compute_source_replication_diagnostics,
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
    assert result["component_mean_gaps"][0]["available"]


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
