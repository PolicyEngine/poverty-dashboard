"""Private audit executes only metadata in the actual gateway and worker functions."""

import importlib
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import modal_app


@pytest.fixture
def audit(monkeypatch):
    module = importlib.import_module("poverty_dashboard.runtime_audit")
    monkeypatch.setattr(
        module, "serving_witness", lambda nonce: {"nonce": nonce, "pid": os.getpid()}
    )
    return module


def test_gateway_audit_is_private_disabled_by_default_and_uncached(audit, monkeypatch):
    monkeypatch.delenv("POVERTY_RUNTIME_AUDIT_TOKEN", raising=False)
    with TestClient(modal_app.web_app.local()) as client:
        assert (
            client.get("/runtime-audit?nonce=fixture-nonce-012345").status_code == 404
        )
        monkeypatch.setenv("POVERTY_RUNTIME_AUDIT_TOKEN", "synthetic-test-only-token")
        assert (
            client.get("/runtime-audit?nonce=fixture-nonce-012345").status_code == 404
        )
        assert (
            client.get(
                "/runtime-audit?nonce=fixture-nonce-012345",
                headers={"Authorization": "Bearer incorrect"},
            ).status_code
            == 404
        )
        response = client.get(
            "/runtime-audit?nonce=fixture-nonce-012345",
            headers={"Authorization": "Bearer synthetic-test-only-token"},
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "runtime_audit": {"nonce": "fixture-nonce-012345", "pid": os.getpid()}
        }


def test_private_route_rejects_invalid_nonce_and_query_before_witness(
    audit, monkeypatch
):
    monkeypatch.setenv("POVERTY_RUNTIME_AUDIT_TOKEN", "synthetic-test-only-token")
    monkeypatch.setattr(
        audit,
        "serving_witness",
        lambda nonce: pytest.fail("Invalid request must not capture"),
    )
    with TestClient(modal_app.web_app.local()) as client:
        for query in (
            "nonce=short",
            "nonce=fixture-nonce-012345&extra=1",
            "nonce=fixture-nonce-012345&nonce=fixture-nonce-678901",
        ):
            assert (
                client.get(
                    "/runtime-audit?" + query,
                    headers={"Authorization": "Bearer synthetic-test-only-token"},
                ).status_code
                == 422
            )


def test_unauthorized_route_never_calls_witness(audit, monkeypatch):
    monkeypatch.setenv("POVERTY_RUNTIME_AUDIT_TOKEN", "synthetic-test-only-token")
    monkeypatch.setattr(
        audit, "serving_witness", lambda nonce: pytest.fail("Unauthenticated witness")
    )
    with TestClient(modal_app.web_app.local()) as client:
        assert (
            client.get("/runtime-audit?nonce=fixture-nonce-012345").status_code == 404
        )


def test_original_worker_audit_branches_precede_calculation(audit, monkeypatch):
    monkeypatch.setattr(
        modal_app.subprocess,
        "run",
        lambda *a, **kw: pytest.fail("No calculation subprocess"),
    )
    expected = {"runtime_audit": {"nonce": "fixture-nonce-012345", "pid": os.getpid()}}
    assert (
        modal_app.compute_region_remote.local(
            "us", runtime_audit_nonce="fixture-nonce-012345"
        )
        == expected
    )
    assert (
        modal_app.get_versions_remote.local(runtime_audit_nonce="fixture-nonce-012345")
        == expected
    )


def test_public_endpoints_cannot_request_worker_audits(audit):
    with TestClient(modal_app.web_app.local()) as client:
        assert (
            client.get("/versions?runtime_audit_nonce=fixture-nonce-012345").status_code
            == 422
        )
        assert (
            client.post(
                "/recompute?runtime_audit_nonce=fixture-nonce-012345"
            ).status_code
            == 422
        )


def test_default_worker_commands_and_versions_are_unchanged(monkeypatch):
    from poverty_dashboard import versions

    calls = []

    def run(argv, **kwargs):
        from types import SimpleNamespace

        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='{"region_code":"us"}')

    monkeypatch.setattr(modal_app.subprocess, "run", run)
    assert modal_app.compute_region_remote.local("us", 2025) == {"region_code": "us"}
    assert calls == [
        [modal_app.sys.executable, "-m", "poverty_dashboard.poverty_calc", "us", "2025"]
    ]
    monkeypatch.setattr(versions, "installed_versions", lambda: {"fixture": "1"})
    assert modal_app.get_versions_remote.local() == {"fixture": "1"}


def test_real_witness_uses_actual_lightweight_child(monkeypatch):
    import modal

    from poverty_dashboard.runtime_audit import serving_witness

    monkeypatch.setattr(
        modal, "current_function_call_id", lambda: "fc-synthetic-context"
    )
    monkeypatch.setattr(modal, "current_input_id", lambda: "in-synthetic-context")
    result = serving_witness("fixture-nonce-012345")
    assert result["pid"] == os.getpid()
    assert result["child"]["pid"] != result["pid"]
    assert result["input_id"] == "in-synthetic-context"
    for field in ("executable", "prefix", "base_prefix"):
        assert result[field] == result["child"][field]
    assert result["already_loaded_module_origins"][
        "poverty_dashboard.runtime_audit"
    ] == str(Path(__file__).resolve().parents[1] / "poverty_dashboard/runtime_audit.py")
    assert result["modal_context_available"] is True
    assert "captured_in_serving_handler" not in result
    assert result["child"]["sys_path"]
    assert "policyengine-core" in result["child"]["packages"]
    assert "not loaded" in result["module_origin_note"]
    assert "environment" not in result
    with pytest.raises(ValueError, match="nonce"):
        serving_witness("invalid")


def test_audit_failure_is_controlled_and_uncached(audit, monkeypatch):
    monkeypatch.setenv("POVERTY_RUNTIME_AUDIT_TOKEN", "synthetic-test-only-token")

    def failed(nonce):
        raise RuntimeError("private-fixture-failure-detail")

    monkeypatch.setattr(audit, "serving_witness", failed)
    with TestClient(modal_app.web_app.local()) as client:
        response = client.get(
            "/runtime-audit?nonce=fixture-nonce-012345",
            headers={"Authorization": "Bearer synthetic-test-only-token"},
        )
    assert response.status_code == 502
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"detail": "Runtime audit failed."}
