"""Trigger a recompute on the deployed Modal app and write data/baseline.json.

Usage:
    python -m scripts.precompute_baseline                     # use installed versions
    python -m scripts.precompute_baseline --upgrade           # pip -U first
    python -m scripts.precompute_baseline --url https://...   # explicit endpoint
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlencode

import urllib.request


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = REPO_ROOT / "data" / "baseline.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("MODAL_BASE_URL"))
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_BASELINE))
    args = parser.parse_args()

    if not args.url:
        raise SystemExit(
            "MODAL_BASE_URL not set and --url not provided. After `modal deploy "
            "modal_app.py`, set MODAL_BASE_URL to the printed web_app URL."
        )

    qs = urlencode({"upgrade": "true" if args.upgrade else "false"})
    endpoint = f"{args.url.rstrip('/')}/recompute?{qs}"
    req = urllib.request.Request(endpoint, method="POST")
    with urllib.request.urlopen(req, timeout=2400) as resp:
        payload = json.load(resp)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {args.out} ({len(payload.get('regions', {}))} regions, "
          f"{len(payload.get('errors', []))} errors)")


if __name__ == "__main__":
    main()
