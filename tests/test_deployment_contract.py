"""Inspect actual Modal build instructions without building an image."""

from __future__ import annotations

import ast
import importlib.util
import re
import shlex
import subprocess
from pathlib import Path

from modal.image import _Image

ROOT = Path(__file__).resolve().parents[1]


def _git_ignores(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )


def _modal_function_limits() -> dict[str, dict[str, float]]:
    """Read the declared cpu/memory/timeout off each ``@app.function``."""
    limits: dict[str, dict[str, float]] = {}
    for node in ast.parse((ROOT / "modal_app.py").read_text()).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else None
            if not (isinstance(target, ast.Attribute) and target.attr == "function"):
                continue
            limits[node.name] = {
                keyword.arg: ast.literal_eval(keyword.value)
                for keyword in decorator.keywords
                if keyword.arg in {"cpu", "memory", "timeout"}
            }
    return limits


def _git_tracks(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def test_modal_dependency_layer_uses_committed_lock(monkeypatch):
    recipes = []
    original = _Image._from_args

    def capture_recipe(**kwargs):
        if recipe := kwargs.get("dockerfile_function"):
            recipes.append(recipe)
        return original(**kwargs)

    monkeypatch.setattr(_Image, "_from_args", staticmethod(capture_recipe))
    monkeypatch.chdir(ROOT)
    spec = importlib.util.spec_from_file_location(
        "poverty_modal_contract_probe", ROOT / "modal_app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    layers = [recipe("2025.06") for recipe in recipes]
    dependency_layers = [
        layer
        for layer in layers
        if any("/uv sync " in command for command in layer.commands)
    ]
    assert len(dependency_layers) == 1, "Modal must install the locked closure"
    layer = dependency_layers[0]
    for filename in ("pyproject.toml", "uv.lock"):
        assert Path(layer.context_files[f"/.{filename}"]).resolve() == ROOT / filename
    command = next(c for c in layer.commands if "/uv sync " in c)
    flags = shlex.split(command)
    assert "--locked" in flags, "Missing or stale locks must fail the build"
    assert "--frozen" not in flags, "Frozen alone ignores stale project metadata"
    assert "--no-dev" in flags
    assert "--no-install-workspace" in flags
    assert "COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /.uv/uv" in layer.commands
    assert "ENV PATH=/.uv/.venv/bin:$PATH" in layer.commands


def test_local_install_preserves_the_lock():
    makefile = (ROOT / "Makefile").read_text()
    install = makefile.split("install-python:\n", 1)[1].split("\n\n", 1)[0]
    assert "uv sync --extra dev --locked" in install
    assert "uv pip install" not in install
    deploy = makefile.split("deploy:\n", 1)[1].split("\n\n", 1)[0]
    assert "uv run --locked modal deploy modal_app.py" in deploy


def test_materialized_population_cannot_be_staged_beside_the_numeric_assets():
    from policyengine.provenance.dataset_materialization import DEFAULT_DATA_DIR
    from policyengine.provenance.manifest import get_release_manifest

    # Materialization resolves ./data against the working directory, and the
    # documented CLI invocations run from the repo root.
    assert DEFAULT_DATA_DIR == Path("./data")

    manifest = get_release_manifest("us")
    reference = manifest.datasets[manifest.default_dataset]
    destination = DEFAULT_DATA_DIR / Path(reference.path).name
    for materialized in (
        destination,
        Path(f"{destination}.metadata.json"),
        DEFAULT_DATA_DIR / ".policyengine-download-fixture.h5",
    ):
        assert _git_ignores(materialized), f"`git add data` would stage {materialized}"

    for asset in ("baseline.json", "census_spm_2024.json", "spm_gap_diagnostics.json"):
        protected = Path("data") / asset
        assert not _git_ignores(protected)
        assert _git_tracks(protected)


def test_cost_guidance_matches_the_national_population_fan_out():
    from poverty_dashboard.regions import all_region_codes

    limits = _modal_function_limits()
    worker = limits["compute_region_remote"]
    gateway = limits["web_app"]
    deployment = (ROOT / "DEPLOYMENT.md").read_text()
    readme = (ROOT / "README.md").read_text()

    # Superseded when every region became a national-size run.
    assert "(~30 min)" not in deployment
    assert "51 containers in parallel" not in readme

    for text in (readme.split("## Cost notes", 1)[1], deployment):
        assert f"{len(all_region_codes())} regions" in text
        assert "national population" in text
        assert f"cpu {worker['cpu']}" in text
        assert f"{worker['memory']} MiB" in text
        assert f"{worker['timeout']} s" in text
        assert f"{gateway['timeout']} s" in text


def test_protection_document_link_resolves():
    readme = (ROOT / "README.md").read_text()
    paragraph = readme.split("The diagnostic scripts", 1)[1].split("\n\n", 1)[0]
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", paragraph)
    assert links, "Protection guidance must link to a checked-in document"
    assert all((ROOT / link).is_file() for link in links)
