"""Run poverty calculations locally without Modal."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime

from poverty_dashboard.paths import DEFAULT_BASELINE, FRONTEND_PUBLIC_BASELINE
from poverty_dashboard.poverty_calc import YEAR, compute_region
from poverty_dashboard.regions import all_region_codes
from poverty_dashboard.versions import installed_versions


def build_empty_baseline(year: int) -> dict:
    """Create the baseline JSON envelope used by backend and frontend."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "year": year,
        "versions": installed_versions(),
        "regions": {},
        "errors": [],
    }


def main() -> None:
    """Run selected regions locally and write ``data/baseline.json``."""
    parser = argparse.ArgumentParser()
    parser.add_argument("regions", nargs="*")
    parser.add_argument("--year", type=int, default=YEAR)
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Start from existing baseline.json instead of overwriting",
    )
    args = parser.parse_args()

    codes = all_region_codes() if args.all else (args.regions or ["us"])
    payload = build_empty_baseline(args.year)

    if args.merge and DEFAULT_BASELINE.exists():
        existing = json.loads(DEFAULT_BASELINE.read_text())
        if (
            existing.get("year") != args.year
            or existing.get("versions") != payload["versions"]
        ):
            raise SystemExit(
                "Cannot merge baselines from different years or runtime bundles. "
                "Preserve the existing snapshot and regenerate a separate baseline."
            )
        payload["regions"] = existing.get("regions", {})
        payload["errors"] = existing.get("errors", [])

    for index, code in enumerate(codes, 1):
        print(f"[{index}/{len(codes)}] {code} ...", flush=True)
        try:
            result = compute_region(code, year=args.year)
        except Exception as exc:
            print(f"  ERROR: {exc}", flush=True)
            payload["errors"].append({"region_code": code, "error": str(exc)})
            continue

        payload["regions"][code] = {
            "region_code": code,
            "dataset_path": result["dataset_path"],
            "policyengine_bundle": result["policyengine_bundle"],
            "region_scope": result["region_scope"],
            "versions": result["versions"],
            "people": result["people"],
            "child_count": result["child_count"],
            "rates": result["rates"],
            "deep_rates": result["deep_rates"],
        }
        rates = result["rates"]
        print(
            f"  poverty={rates['all'] * 100:.2f}%  "
            f"child={rates['child'] * 100:.2f}%  "
            f"people={result['people']:,.0f}",
            flush=True,
        )

    DEFAULT_BASELINE.write_text(json.dumps(payload, indent=2) + "\n")
    FRONTEND_PUBLIC_BASELINE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEFAULT_BASELINE, FRONTEND_PUBLIC_BASELINE)
    print(f"Wrote {DEFAULT_BASELINE} and copied to {FRONTEND_PUBLIC_BASELINE}")


if __name__ == "__main__":
    main()
