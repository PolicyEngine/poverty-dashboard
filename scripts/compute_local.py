"""Run poverty calcs locally (no Modal) and write data/baseline.json.

Usage:
    python -m scripts.compute_local us              # just federal
    python -m scripts.compute_local us state/ca state/ny
    python -m scripts.compute_local --all           # federal + all 51 states
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .poverty_calc import compute_region
from .regions import all_region_codes
from .versions import installed_versions

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "data" / "baseline.json"
FRONTEND_PUBLIC = REPO_ROOT / "frontend" / "public" / "baseline.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("regions", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--merge", action="store_true",
                        help="Start from existing baseline.json instead of overwriting")
    args = parser.parse_args()

    codes = all_region_codes() if args.all else (args.regions or ["us"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "year": 2026,
        "versions": installed_versions(),
        "regions": {},
        "errors": [],
    }

    if args.merge and OUT.exists():
        existing = json.loads(OUT.read_text())
        payload["regions"] = existing.get("regions", {})
        payload["errors"] = existing.get("errors", [])

    for i, code in enumerate(codes, 1):
        print(f"[{i}/{len(codes)}] {code} ...", flush=True)
        try:
            r = compute_region(code)
        except Exception as exc:
            print(f"  ERROR: {exc}", flush=True)
            payload["errors"].append({"region_code": code, "error": str(exc)})
            continue
        payload["regions"][code] = {
            "region_code": code,
            "dataset_path": r["dataset_path"],
            "people": r["people"],
            "child_count": r["child_count"],
            "rates": r["rates"],
            "deep_rates": r["deep_rates"],
        }
        rates = r["rates"]
        print(
            f"  poverty={rates['all']*100:.2f}%  child={rates['child']*100:.2f}%  "
            f"people={r['people']:,.0f}",
            flush=True,
        )

    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    FRONTEND_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUT, FRONTEND_PUBLIC)
    print(f"Wrote {OUT} and copied to {FRONTEND_PUBLIC}")


if __name__ == "__main__":
    main()
