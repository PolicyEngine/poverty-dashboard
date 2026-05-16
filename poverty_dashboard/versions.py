"""Read installed versions of packages that drive the dashboard."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

PACKAGES = ["policyengine", "policyengine-us"]


def installed_versions() -> dict[str, str | None]:
    """Return installed versions for PolicyEngine packages used in calculations."""
    out: dict[str, str | None] = {}
    for package in PACKAGES:
        try:
            out[package] = version(package)
        except PackageNotFoundError:
            out[package] = None
    return out
