"""Read installed versions of the packages that drive the dashboard."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


PACKAGES = ["policyengine", "policyengine-us"]


def installed_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for pkg in PACKAGES:
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = None
    return out
