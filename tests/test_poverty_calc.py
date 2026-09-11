from __future__ import annotations

import pytest
from microdf import MicroSeries

from poverty_dashboard.poverty_calc import (
    US_DATASET_ENV,
    compute_region,
    resolve_dataset,
    summarize_poverty,
)
from poverty_dashboard.spm_diagnostics import threshold_ratio_distribution
from poverty_dashboard.spm_elements import (
    SPM_ELEMENTS,
    poverty_effect_from_component,
    spm_unit_component_as_person,
)


def test_us_dataset_env_overrides_national_dataset(monkeypatch) -> None:
    monkeypatch.setenv(US_DATASET_ENV, "/tmp/local-enhanced-cps.h5")

    assert resolve_dataset("us") == "/tmp/local-enhanced-cps.h5"


def test_path_only_resolution_refuses_states_requiring_filtering() -> None:
    with pytest.raises(ValueError, match="requires geographic filtering"):
        resolve_dataset("state/ca")


def test_national_diagnostics_receive_a_verified_local_population_file(monkeypatch):
    """The registry URI names a dataset-type repo the country loader cannot fetch."""
    import inspect

    from policyengine.provenance import dataset_materialization
    from policyengine.provenance.manifest import get_release_manifest
    from policyengine_core.tools.hugging_face import download_huggingface_dataset

    manifest = get_release_manifest("us")
    assert manifest.data_package.repo_type == "dataset"
    assert 'repo_type="model"' in inspect.getsource(download_huggingface_dataset)

    requested = []

    def materialize(country_id, dataset=None, **kwargs):
        requested.append((country_id, dataset, kwargs))
        return dataset_materialization.DatasetSource(
            source_uri=dataset, path="/verified/populace_us_2024.h5"
        )

    monkeypatch.delenv(US_DATASET_ENV, raising=False)
    monkeypatch.setattr(dataset_materialization, "materialize_dataset", materialize)

    assert resolve_dataset("us") == "/verified/populace_us_2024.h5"
    assert requested == [("us", manifest.default_dataset_uri, {})]


def test_compute_state_filters_weighted_people_and_preserves_provenance(monkeypatch):
    import policyengine as pe

    provenance = {
        "runtime_dataset_uri": "test-fixture://managed-population",
        "runtime_dataset_sha256": "fixture-digest",
        "future_provenance_field": {"retained": True},
    }

    class PopulationFixture:
        policyengine_bundle = provenance

        def get_known_periods(self, variable):
            assert variable == "state_fips"
            return [2026]

        def calculate(self, variable, period, map_to="person"):
            assert period == 2026
            assert map_to == "person"
            values = {
                "age": [10, 30, 70, 10],
                "state_fips": [6, 6, 6, 36],
                "spm_unit_is_in_spm_poverty": [True, False, False, True],
                "spm_unit_is_in_deep_spm_poverty": [False, False, False, True],
            }[variable]
            return MicroSeries(values, weights=[1, 2, 3, 100])

    def managed_factory(*, dataset=None, allow_unmanaged=False):
        assert dataset is None
        assert not allow_unmanaged
        return PopulationFixture()

    monkeypatch.delenv(US_DATASET_ENV, raising=False)
    monkeypatch.setattr(pe.us, "managed_microsimulation", managed_factory)
    result = compute_region("state/ca")

    assert result["people"] == 6
    assert result["rates"]["all"] == pytest.approx(1 / 6)
    assert result["dataset_path"] == provenance["runtime_dataset_uri"]
    assert result["policyengine_bundle"] == provenance
    assert result["region_scope"]["variable_value"] == 6


def test_state_filter_refuses_a_population_missing_the_state_fips_input(monkeypatch):
    """An absent column defaults every household to FIPS 6, California."""
    import policyengine as pe

    class PopulationWithoutStateFips:
        policyengine_bundle = {"runtime_dataset_uri": "test-fixture://no-state-fips"}

        def get_known_periods(self, variable):
            assert variable == "state_fips"
            return []

        def calculate(self, variable, period, map_to="person"):
            raise AssertionError("Filtering must be refused before calculating")

    monkeypatch.delenv(US_DATASET_ENV, raising=False)
    monkeypatch.setattr(
        pe.us,
        "managed_microsimulation",
        lambda **kwargs: PopulationWithoutStateFips(),
    )

    with pytest.raises(ValueError, match="would read its default value"):
        compute_region("state/ca")


def test_state_filter_refuses_a_population_whose_state_fips_is_constant(monkeypatch):
    """A defaulted column would hand the whole national population to California."""
    import policyengine as pe

    class DefaultedStateFipsPopulation:
        policyengine_bundle = {"runtime_dataset_uri": "test-fixture://defaulted-fips"}

        def get_known_periods(self, variable):
            return [2026]

        def calculate(self, variable, period, map_to="person"):
            return MicroSeries(
                {
                    "age": [10, 30, 70, 40],
                    "state_fips": [6, 6, 6, 6],
                    "spm_unit_is_in_spm_poverty": [True, False, False, True],
                    "spm_unit_is_in_deep_spm_poverty": [False, False, False, True],
                }[variable],
                weights=[1, 2, 3, 100],
            )

    monkeypatch.delenv(US_DATASET_ENV, raising=False)
    monkeypatch.setattr(
        pe.us,
        "managed_microsimulation",
        lambda **kwargs: DefaultedStateFipsPopulation(),
    )

    with pytest.raises(ValueError, match="holds a single value"):
        compute_region("state/ca")


def test_summarize_poverty_uses_weighted_microseries_operations() -> None:
    age = MicroSeries([10, 25, 70], weights=[1, 2, 3])
    in_poverty = MicroSeries([True, False, True], weights=[1, 2, 3])
    in_deep_poverty = MicroSeries([False, True, True], weights=[1, 2, 3])

    result = summarize_poverty(age, in_poverty, in_deep_poverty)

    assert result["people"] == 6
    assert result["child_count"] == 1
    assert result["rates"]["all"] == pytest.approx(4 / 6)
    assert result["rates"]["child"] == 1
    assert result["rates"]["working_age"] == 0
    assert result["rates"]["senior"] == 1
    assert result["deep_rates"]["all"] == pytest.approx(5 / 6)
    assert result["deep_rates"]["child"] == 0
    assert result["deep_rates"]["working_age"] == 1
    assert result["deep_rates"]["senior"] == 1


def test_compute_region_rejects_unsupported_year_before_loading_dataset() -> None:
    with pytest.raises(ValueError, match="Unsupported year"):
        compute_region("us", year=2023)


def test_threshold_ratio_distribution_uses_weighted_bins() -> None:
    age = MicroSeries([10, 25, 70, 30], weights=[1, 2, 3, 4])
    net_income = MicroSeries([25, 75, 125, 450], weights=[1, 2, 3, 4])
    threshold = MicroSeries([100, 100, 100, 100], weights=[1, 2, 3, 4])

    result = threshold_ratio_distribution(net_income, threshold, age)

    assert result["all"]["less_than_0_50"] == pytest.approx(1 / 10)
    assert result["all"]["from_0_50_to_0_99"] == pytest.approx(2 / 10)
    assert result["all"]["from_1_00_to_1_49"] == pytest.approx(3 / 10)
    assert result["all"]["from_4_00_or_more"] == pytest.approx(4 / 10)
    assert result["child"]["less_than_0_50"] == 1
    assert result["senior"]["from_1_00_to_1_49"] == 1


def test_poverty_effect_from_component_is_arithmetic_without_resimulation() -> None:
    age = MicroSeries([10, 25, 70], weights=[1, 1, 1])
    threshold = MicroSeries([100, 100, 100], weights=[1, 1, 1])
    net_income = MicroSeries([110, 90, 110], weights=[1, 1, 1])
    component = MicroSeries([20, 20, 20], weights=[1, 1, 1])

    addition = poverty_effect_from_component(
        net_income=net_income,
        threshold=threshold,
        component=component,
        age=age,
        section="addition",
    )
    subtraction = poverty_effect_from_component(
        net_income=net_income,
        threshold=threshold,
        component=component,
        age=age,
        section="subtraction",
    )

    assert addition["all"] == pytest.approx(-2 / 3)
    assert subtraction["all"] == pytest.approx(1 / 3)


def test_missing_addition_effect_uses_corrected_baseline_income() -> None:
    age = MicroSeries([10, 25, 70], weights=[1, 1, 1])
    threshold = MicroSeries([100, 100, 100], weights=[1, 1, 1])
    net_income = MicroSeries([90, 90, 110], weights=[1, 1, 1])
    component = MicroSeries([20, 20, 20], weights=[1, 1, 1])

    result = poverty_effect_from_component(
        net_income=net_income,
        threshold=threshold,
        component=component,
        age=age,
        section="addition",
        included_in_net_income=False,
    )

    assert result["all"] == pytest.approx(-2 / 3)


def test_missing_census_addition_rows_are_marked_as_upstream_resource_gaps() -> None:
    elements = {element.label: element for element in SPM_ELEMENTS}

    assert elements["Child support received"].variables == ("child_support_received",)
    assert not elements["Child support received"].included_in_policyengine_net_income
    assert elements["Workers' compensation"].variables == ("workers_compensation",)
    assert not elements["Workers' compensation"].included_in_policyengine_net_income


def test_utility_assistance_combines_energy_and_broadband_components() -> None:
    elements = {element.label: element for element in SPM_ELEMENTS}

    assert elements["Utility assistance"].variables == (
        "spm_unit_energy_subsidy",
        "acp",
        "ebb",
    )
    assert elements["Energy assistance"].variables == ("spm_unit_energy_subsidy",)
    assert elements["Broadband Assistance"].variables == ("acp", "ebb")


def test_federal_income_tax_effect_uses_tax_before_refundable_credits() -> None:
    federal_tax = next(
        element for element in SPM_ELEMENTS if element.label == "Federal income tax"
    )

    assert federal_tax.variables == ("income_tax_before_refundable_credits",)


def test_state_tax_diagnostics_split_refundable_credits() -> None:
    elements = {element.label: element for element in SPM_ELEMENTS}

    assert elements["State refundable tax credits"].section == "addition"
    assert elements["State refundable tax credits"].variables == (
        "state_refundable_credits",
    )
    assert (
        elements["State income tax before refundable credits"].section == "subtraction"
    )
    assert elements["State income tax before refundable credits"].variables == (
        "state_income_tax_before_refundable_credits",
    )


def test_spm_unit_component_projection_uses_policyengine_entity_mapping() -> None:
    class FakeSim:
        def calculate(self, variable: str, period: int, map_to: str) -> MicroSeries:
            assert period == 2024
            assert map_to == "spm_unit"
            values = {"a": [10, 20], "b": [1, 2]}[variable]
            return MicroSeries(values, weights=[100, 200])

        def map_result(
            self,
            values: object,
            source_entity: str,
            target_entity: str,
        ) -> list[int]:
            assert list(values) == [11, 22]
            assert source_entity == "spm_unit"
            assert target_entity == "person"
            return [11, 22, 22]

    person_reference = MicroSeries([30, 40, 50], weights=[1, 2, 3])

    result = spm_unit_component_as_person(
        sim=FakeSim(),
        variables=("a", "b"),
        year=2024,
        person_reference=person_reference,
    )

    assert result is not None
    assert list(result) == [11, 22, 22]
    assert list(result.weights) == [1, 2, 3]
