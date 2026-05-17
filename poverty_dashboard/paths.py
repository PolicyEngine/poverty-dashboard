"""Filesystem paths shared by dashboard CLI tools."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DEFAULT_BASELINE = DATA_DIR / "baseline.json"
FRONTEND_PUBLIC_BASELINE = REPO_ROOT / "frontend" / "public" / "baseline.json"
