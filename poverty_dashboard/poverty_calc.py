"""Single-region poverty rate calculation."""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from importlib import metadata
from typing import Any

from poverty_dashboard.regions import region_state_code
from poverty_dashboard.simulation import calc

YEAR = 2026
SUPPORTED_YEARS = [2024, 2025, 2026]
US_DATA_ROOT = "hf://policyengine/policyengine-us-data"
US_DATASET_ENV = "POVERTY_DASHBOARD_US_DATASET"
US_RELEASE_MANIFEST = "policyengine/data/release_manifests/us.json"


def _build_hf_uri(repo_id: str, path_in_repo: str, revision: str) -> str:
    return f"hf://{repo_id}/{path_in_repo}@{revision}"


@lru_cache
def _policyengine_us_manifest() -> dict[str, Any]:
    """Read the bundled US release manifest without importing PolicyEngine."""
    distribution = metadata.distribution("policyengine")
    manifest_path = distribution.locate_file(US_RELEASE_MANIFEST)
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def _manifest_artifact_uri(dataset: str) -> str:
    reference = _manifest_artifact_reference(dataset)
    return _build_hf_uri(
        reference["repo_id"],
        reference["path"],
        reference["revision"],
    )


def _manifest_artifact_reference(dataset: str) -> dict[str, str]:
    manifest = _policyengine_us_manifest()
    certified_artifact = manifest.get("certified_data_artifact")
    if (
        dataset == manifest.get("default_dataset")
        and certified_artifact is not None
        and certified_artifact.get("dataset") == dataset
    ):
        repo_id, path, revision = _parse_hf_uri(certified_artifact["uri"])
        return {
            "repo_id": repo_id,
            "repo_type": manifest["data_package"].get("repo_type", "model"),
            "path": path,
            "revision": revision,
        }

    path_reference = manifest.get("datasets", {}).get(dataset)
    if path_reference is None:
        raise ValueError(
            f"Unknown dataset '{dataset}' in policyengine.py US release manifest"
        )

    data_package = manifest["data_package"]
    revision = (
        path_reference.get("revision")
        or data_package.get("release_manifest_revision")
        or data_package["version"]
    )
    repo_id = path_reference.get("repo_id") or data_package["repo_id"]
    repo_type = (
        data_package.get("repo_type", "model")
        if repo_id == data_package["repo_id"]
        else path_reference.get("repo_type", "model")
    )
    return {
        "repo_id": repo_id,
        "repo_type": repo_type,
        "path": path_reference["path"],
        "revision": revision,
    }


def _parse_hf_uri(uri: str) -> tuple[str, str, str]:
    if not uri.startswith("hf://") or "@" not in uri:
        raise ValueError(f"Expected revisioned Hugging Face URI, got: {uri}")

    without_scheme = uri[5:]
    repo_and_path, revision = without_scheme.rsplit("@", 1)
    owner, repo, path = repo_and_path.split("/", 2)
    return f"{owner}/{repo}", path, revision


def _download_hf_artifact(reference: dict[str, str]) -> str:
    from huggingface_hub import hf_hub_download

    try:
        return hf_hub_download(
            repo_id=reference["repo_id"],
            filename=reference["path"],
            revision=reference["revision"],
            repo_type=reference["repo_type"],
        )
    except Exception:
        return hf_hub_download(
            repo_id=reference["repo_id"],
            filename=reference["path"],
            revision=reference["revision"],
            repo_type=reference["repo_type"],
            local_files_only=True,
        )


def _dataset_key(region_code: str) -> str:
    if region_code == "us":
        return _policyengine_us_manifest()["default_dataset"]

    abbrev = region_state_code(region_code)
    if abbrev is None:
        raise ValueError(f"Unsupported region: {region_code}")
    return f"states/{abbrev}"


def fallback_dataset(region_code: str) -> str:
    """Return the policyengine.py bundled dataset path for a region."""
    if region_code == "us":
        if configured := os.environ.get(US_DATASET_ENV):
            return configured
    return _manifest_artifact_uri(_dataset_key(region_code))


def resolve_dataset(region_code: str) -> str:
    """Resolve the dataset path from the installed policyengine.py bundle."""
    return fallback_dataset(region_code)


def resolve_dataset_source(region_code: str) -> str:
    """Resolve a loadable dataset path while keeping canonical output separate."""
    if region_code == "us" and (configured := os.environ.get(US_DATASET_ENV)):
        return configured

    reference = _manifest_artifact_reference(_dataset_key(region_code))
    if reference["repo_type"] == "dataset":
        return _download_hf_artifact(reference)
    return _manifest_artifact_uri(_dataset_key(region_code))


def summarize_poverty(
    age: Any, in_poverty: Any, in_deep_poverty: Any
) -> dict[str, Any]:
    """Summarize person-level poverty rates using weighted MicroSeries operations."""
    is_person = age >= 0
    is_child = age < 18
    is_working_age = (age >= 18) & (age < 65)
    is_senior = age >= 65

    return {
        "people": float(is_person.sum()),
        "child_count": float(is_child.sum()),
        "rates": {
            "all": float(in_poverty.mean()),
            "child": float(in_poverty[is_child].mean()),
            "working_age": float(in_poverty[is_working_age].mean()),
            "senior": float(in_poverty[is_senior].mean()),
        },
        "deep_rates": {
            "all": float(in_deep_poverty.mean()),
            "child": float(in_deep_poverty[is_child].mean()),
            "working_age": float(in_deep_poverty[is_working_age].mean()),
            "senior": float(in_deep_poverty[is_senior].mean()),
        },
    }


def compute_region(region_code: str, year: int = YEAR) -> dict[str, Any]:
    """Compute baseline poverty rates for one region."""
    from policyengine_us import Microsimulation

    if year not in SUPPORTED_YEARS:
        raise ValueError(
            f"Unsupported year: {year}. Expected one of {SUPPORTED_YEARS}."
        )

    dataset_path = resolve_dataset(region_code)
    dataset_source = resolve_dataset_source(region_code)
    sim = Microsimulation(dataset=dataset_source)

    age = calc(sim, "age", period=year)
    in_poverty = calc(
        sim,
        "spm_unit_is_in_spm_poverty",
        period=year,
        map_to="person",
    )
    in_deep_poverty = calc(
        sim,
        "spm_unit_is_in_deep_spm_poverty",
        period=year,
        map_to="person",
    )

    return {
        "region_code": region_code,
        "dataset_path": dataset_path,
        "year": year,
        **summarize_poverty(age, in_poverty, in_deep_poverty),
    }


def main() -> None:
    """Run the single-region calculation CLI."""
    if len(sys.argv) < 2:
        print(
            "usage: python -m poverty_dashboard.poverty_calc <region_code> [year]",
            file=sys.stderr,
        )
        sys.exit(2)
    year = int(sys.argv[2]) if len(sys.argv) > 2 else YEAR
    result = compute_region(sys.argv[1], year=year)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
