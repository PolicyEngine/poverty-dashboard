"""Modal deployment for the PolicyEngine internal poverty dashboard.

Endpoints:

    GET  /baseline                — return the committed baseline.json
    GET  /versions                — installed package versions on the worker
    POST /recompute?year=2026     — fan-out across regions, return fresh JSON
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC
from pathlib import Path

import modal
from fastapi import Request

APP_NAME = os.environ.get("MODAL_APP_NAME", "poverty-dashboard")

app = modal.App(APP_NAME)

# --locked rejects missing/stale locks; --frozen would skip the staleness check.
# Local code is copied separately because uv_sync installs only dependencies.
image = (
    modal.Image.debian_slim(python_version="3.14")
    .apt_install("git")
    .uv_sync(
        frozen=False,
        extra_options="--locked --no-dev",
        uv_version="0.11.7",
    )
    .add_local_python_source("poverty_dashboard", copy=True)
)


@app.function(image=image, cpu=2.0, memory=8192, timeout=1200)
def compute_region_remote(
    region_code: str,
    year: int = 2026,
) -> dict:
    """Run a single-region poverty calc in an isolated subprocess."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "poverty_dashboard.poverty_calc",
            region_code,
            str(year),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "region_code": region_code,
            "error": proc.stderr.strip()[-2000:],
        }

    return json.loads(proc.stdout)


@app.function(image=image, cpu=1.0, memory=2048, timeout=60)
def get_versions_remote() -> dict:
    from poverty_dashboard.versions import installed_versions

    return installed_versions()


@app.function(image=image, cpu=1.0, memory=2048, timeout=2400)
@modal.asgi_app()
def web_app():
    from datetime import datetime

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from poverty_dashboard.poverty_calc import SUPPORTED_YEARS, YEAR
    from poverty_dashboard.regions import all_region_codes

    api = FastAPI(title="PolicyEngine Poverty Dashboard", version="0.1.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    baseline_path = Path(__file__).parent / "data" / "baseline.json"

    def require_known_query(request: Request, allowed: set[str]) -> None:
        unexpected = set(request.query_params) - allowed
        if unexpected:
            raise HTTPException(422, f"Unknown query parameters: {sorted(unexpected)}")

    @api.get("/health")
    def health():
        return {"ok": True}

    @api.get("/baseline")
    def baseline():
        if not baseline_path.exists():
            raise HTTPException(404, "baseline.json not found — run /recompute")
        return json.loads(baseline_path.read_text())

    @api.get("/versions")
    def versions(request: Request):
        require_known_query(request, set())
        return get_versions_remote.remote()

    @api.post("/recompute")
    def recompute(request: Request, year: int = YEAR):
        require_known_query(request, {"year"})
        if year not in SUPPORTED_YEARS:
            raise HTTPException(400, f"Unsupported year: {year}")

        codes = all_region_codes()

        # Fan out: each container runs one region in parallel.
        args = [(code, year) for code in codes]
        results = list(compute_region_remote.starmap(args))

        regions: dict[str, dict] = {}
        errors: list[dict] = []
        last_versions: dict | None = None
        for r in results:
            code = r["region_code"]
            if "error" in r:
                errors.append({"region_code": code, "error": r["error"]})
                continue
            last_versions = r.get("versions", last_versions)
            regions[code] = {
                "region_code": code,
                "dataset_path": r["dataset_path"],
                "policyengine_bundle": r["policyengine_bundle"],
                "region_scope": r["region_scope"],
                "versions": r["versions"],
                "people": r["people"],
                "child_count": r["child_count"],
                "rates": r["rates"],
                "deep_rates": r["deep_rates"],
            }

        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "year": year,
            "versions": last_versions or {},
            "regions": regions,
            "errors": errors,
        }
        return payload

    return api
