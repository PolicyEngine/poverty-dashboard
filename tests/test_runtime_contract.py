"""Check supported installed APIs and the public recompute contract without data."""

from __future__ import annotations

import inspect

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
