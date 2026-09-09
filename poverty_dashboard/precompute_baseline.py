"""Trigger a recompute on the deployed Modal app and write baseline JSON."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from poverty_dashboard.paths import DEFAULT_BASELINE
from poverty_dashboard.poverty_calc import YEAR


def main() -> None:
    """Call the Modal recompute endpoint and write the resulting JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("MODAL_BASE_URL"))
    parser.add_argument("--year", type=int, default=YEAR)
    parser.add_argument("--out", default=str(DEFAULT_BASELINE))
    args = parser.parse_args()

    if not args.url:
        raise SystemExit(
            "MODAL_BASE_URL not set and --url not provided. After `modal deploy "
            "modal_app.py`, set MODAL_BASE_URL to the printed web_app URL."
        )

    query = urlencode(
        {
            "year": str(args.year),
        }
    )
    endpoint = f"{args.url.rstrip('/')}/recompute?{query}"
    request = urllib.request.Request(endpoint, method="POST")
    with urllib.request.urlopen(request, timeout=2400) as response:
        payload = json.load(response)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"Wrote {out} ({len(payload.get('regions', {}))} regions, "
        f"{len(payload.get('errors', []))} errors)"
    )


if __name__ == "__main__":
    main()
