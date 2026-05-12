"""Modal deployment for the PolicyEngine internal poverty dashboard.

Endpoints:

    GET  /baseline                — return the committed baseline.json
    GET  /versions                — installed package versions on the worker
    POST /recompute?upgrade=bool  — fan-out across 51 regions, return fresh JSON
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import modal


APP_NAME = os.environ.get("MODAL_APP_NAME", "poverty-dashboard")

app = modal.App(APP_NAME)

# Unpinned policyengine[us] so a fresh deploy bakes in the current latest, and
# the in-function ``pip install -U`` (when upgrade=true) tops it off without
# rebuilding the image.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "fastapi>=0.115.0",
        "pydantic>=2.0",
        "tables>=3.10.2",
        "policyengine[us]",
    )
    .add_local_python_source("scripts", copy=True)
)


def _maybe_upgrade(upgrade: bool) -> None:
    if not upgrade:
        return
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--upgrade", "--quiet",
            "policyengine", "policyengine-us", "policyengine-us-data",
        ],
        check=True,
    )


@app.function(image=image, cpu=2.0, memory=8192, timeout=1200)
def compute_region_remote(region_code: str, upgrade: bool = False) -> dict:
    """Run a single-region poverty calc inside its own subprocess.

    Subprocess isolation matters: when ``upgrade=True`` we just pip-installed
    new wheels into this container, and an already-imported policyengine_us
    would still hold the old code. A fresh interpreter sidesteps that.
    """
    from scripts.versions import installed_versions

    _maybe_upgrade(upgrade)

    proc = subprocess.run(
        [sys.executable, "-m", "scripts.poverty_calc", region_code],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "region_code": region_code,
            "error": proc.stderr.strip()[-2000:],
        }

    result = json.loads(proc.stdout)
    result["versions"] = installed_versions()
    return result


@app.function(image=image, cpu=1.0, memory=2048, timeout=60)
def get_versions_remote(upgrade: bool = False) -> dict:
    from scripts.versions import installed_versions
    _maybe_upgrade(upgrade)
    return installed_versions()


@app.function(image=image, cpu=1.0, memory=2048, timeout=2400)
@modal.asgi_app()
def web_app():
    from datetime import datetime, timezone

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from scripts.regions import all_region_codes

    api = FastAPI(title="PolicyEngine Poverty Dashboard", version="0.1.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    baseline_path = Path(__file__).parent / "data" / "baseline.json"

    @api.get("/health")
    def health():
        return {"ok": True}

    @api.get("/baseline")
    def baseline():
        if not baseline_path.exists():
            raise HTTPException(404, "baseline.json not found — run /recompute")
        return json.loads(baseline_path.read_text())

    @api.get("/versions")
    def versions(upgrade: bool = False):
        return get_versions_remote.remote(upgrade=upgrade)

    @api.post("/recompute")
    def recompute(upgrade: bool = False):
        codes = all_region_codes()

        # Fan out: each container runs one region in parallel.
        args = [(code, upgrade) for code in codes]
        results = list(compute_region_remote.starmap(args))

        regions: dict[str, dict] = {}
        errors: list[dict] = []
        last_versions: dict | None = None
        last_dataset: str | None = None
        for r in results:
            code = r["region_code"]
            if "error" in r:
                errors.append({"region_code": code, "error": r["error"]})
                continue
            last_versions = r.get("versions", last_versions)
            last_dataset = r.get("dataset_path", last_dataset)
            regions[code] = {
                "region_code": code,
                "dataset_path": r["dataset_path"],
                "people": r["people"],
                "child_count": r["child_count"],
                "rates": r["rates"],
                "deep_rates": r["deep_rates"],
            }

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "year": 2026,
            "versions": last_versions or {},
            "regions": regions,
            "errors": errors,
        }
        return payload

    return api
