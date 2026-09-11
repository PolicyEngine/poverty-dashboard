"""Check supported installed APIs and the public recompute contract without data."""

from __future__ import annotations

import inspect
import json

import pytest
from fastapi.testclient import TestClient

import modal_app


def test_obsolete_query_is_rejected_before_remote_execution():
    api = modal_app.web_app.local()
    client = TestClient(api)
    assert client.get("/versions?upgrade=true").status_code == 422
    assert client.post("/recompute?upgrade=true").status_code == 422
    schema = api.openapi()
    for path, method in (("/versions", "get"), ("/recompute", "post")):
        assert "upgrade" not in {
            parameter["name"]
            for parameter in schema["paths"][path][method].get("parameters", [])
        }


def test_installed_wrapper_and_country_support_managed_weighted_calculations():
    import policyengine as pe
    from policyengine.countries.us.regions import us_region_registry
    from policyengine_us import Microsimulation
    from spm_calculator import HISTORICAL_THRESHOLDS, get_latest_published_year
    from spm_calculator.geoadj import get_cd_geoadj

    inspect.signature(pe.us.managed_microsimulation).bind(
        dataset=None, allow_unmanaged=False
    )
    inspect.signature(Microsimulation.calculate).bind(
        None, "state_fips", period=2026, map_to="person"
    )
    assert (
        us_region_registry.get("state/ca").scoping_strategy.variable_name
        == "state_fips"
    )
    assert HISTORICAL_THRESHOLDS
    assert callable(get_latest_published_year)
    assert callable(get_cd_geoadj)


@pytest.mark.parametrize("managed", [True, False], ids=["managed", "explicit-local"])
def test_real_wrapper_runtime_dataset_provenance_reaches_result(monkeypatch, managed):
    from microdf import MicroSeries
    from policyengine.countries.us.regions import us_region_registry
    from policyengine.provenance.dataset_materialization import MaterializedDataset
    from policyengine.provenance.manifest import get_release_manifest
    from policyengine.tax_benefit_models.common.model_version import (
        build_runtime_dataset_provenance,
    )

    from poverty_dashboard import poverty_calc

    # Only the provenance helper is real: no H5 is read and no model is constructed.
    manifest = get_release_manifest("us")
    local_path = "/test-fixture/population.h5"
    source_uri = manifest.default_dataset_uri if managed else local_path
    materialized = (
        MaterializedDataset(
            data_package_name=manifest.data_package.name,
            repo_type="dataset",
            revision="test-fixture-revision",
            source_uri=source_uri,
            sha256="a" * 64,
            path=local_path,
        )
        if managed
        else None
    )
    provenance = build_runtime_dataset_provenance(source_uri, local_path, materialized)
    assert provenance["runtime_dataset_uri"] == source_uri
    assert provenance["runtime_dataset_source"] == local_path
    if managed:
        assert provenance["runtime_dataset_sha256"] == materialized.sha256
        assert provenance["runtime_dataset_revision"] == materialized.revision

    class PopulationFixture:
        policyengine_bundle = provenance

        def calculate(self, variable, period, map_to="person"):
            assert period == 2026
            assert map_to == "person"
            values = [10, 30, 70] if variable == "age" else [True, False, False]
            return MicroSeries(values, weights=[1, 2, 3])

    monkeypatch.setattr(
        poverty_calc,
        "build_region_simulation",
        lambda region: (PopulationFixture(), us_region_registry.get(region)),
    )
    result = poverty_calc.compute_region("us")
    assert result["dataset_path"] == source_uri
    assert result["policyengine_bundle"] == provenance
    assert json.loads(json.dumps(result))["dataset_path"] == source_uri


@pytest.mark.parametrize("region_code", ["us", "state/ca"])
def test_local_override_is_forwarded_only_for_national_region(monkeypatch, region_code):
    import policyengine as pe

    from poverty_dashboard import poverty_calc

    local_path = "/test-fixture/explicit-national.h5"
    monkeypatch.setenv(poverty_calc.US_DATASET_ENV, local_path)
    sentinel = object()
    calls = []

    def managed_factory(*, dataset, allow_unmanaged):
        calls.append({"dataset": dataset, "allow_unmanaged": allow_unmanaged})
        return sentinel

    monkeypatch.setattr(pe.us, "managed_microsimulation", managed_factory)
    sim, region = poverty_calc.build_region_simulation(region_code)
    assert sim is sentinel
    assert region is not None
    assert calls == [
        {
            "dataset": local_path if region_code == "us" else None,
            "allow_unmanaged": region_code == "us",
        }
    ]
