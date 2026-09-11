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


def _prose(text: str) -> str:
    """Collapse the hard wrapping so a phrase assertion can span a line break."""
    return " ".join(text.split())


def _git_ignore_rule(path: Path) -> str | None:
    """Return the .gitignore pattern that excludes ``path``, or None.

    Naming the matching pattern, rather than only asking whether the path is
    ignored, keeps each rule individually pinned: a broader rule that happens to
    cover the same fixture can no longer stand in for a deleted one.
    """
    result = subprocess.run(
        ["git", "check-ignore", "-v", str(path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    source, _, _ = result.stdout.partition("\t")
    return source.rsplit(":", 1)[-1]


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

    # mkstemp uses the destination's suffix, or ".download" when it has none, so
    # the temporaries are only covered by the prefix rule.
    expected_rules = {
        destination: "data/*.h5",
        Path(f"{destination}.metadata.json"): "data/*.metadata.json",
        DEFAULT_DATA_DIR
        / ".policyengine-download-fixture.download": "data/.policyengine-download-*",
        DEFAULT_DATA_DIR
        / ".policyengine-download-fixture.json": "data/.policyengine-download-*",
    }
    for materialized, rule in expected_rules.items():
        matched = _git_ignore_rule(materialized)
        assert matched is not None, f"`git add data` would stage {materialized}"
        assert matched == rule, f"{materialized} is ignored by {matched}, not {rule}"

    for asset in ("baseline.json", "census_spm_2024.json", "spm_gap_diagnostics.json"):
        protected = Path("data") / asset
        assert _git_ignore_rule(protected) is None
        assert _git_tracks(protected)


def test_this_runtime_writes_no_dataset_metadata_sibling():
    """The ignore rule for it is defensive, and DEPLOYMENT.md must not overclaim."""
    from policyengine.provenance.manifest import get_release_manifest

    manifest = get_release_manifest("us")
    reference = manifest.datasets[manifest.default_dataset]

    # _reuse_or_download_bundle_files only fetches the sibling when the manifest
    # certifies its digest.
    assert reference.metadata_sha256 is None

    deployment = _prose((ROOT / "DEPLOYMENT.md").read_text())
    assert "writes no `.metadata.json` sibling" in deployment


def test_worker_cpu_and_memory_are_documented_as_reservations():
    """Modal treats scalar cpu/memory as a request, so the docs must not say limit."""
    from modal._resources import convert_fn_config_to_resources_config

    worker = _modal_function_limits()["compute_region_remote"]
    resources = convert_fn_config_to_resources_config(
        cpu=worker["cpu"],
        memory=worker["memory"],
        gpu=None,
        ephemeral_disk=None,
    )
    assert resources.milli_cpu == int(worker["cpu"] * 1000)
    assert resources.memory_mb == worker["memory"]
    # 0 / unset are Modal's "no ceiling" encodings for a scalar request.
    assert resources.memory_mb_max == 0
    assert not resources.milli_cpu_max

    readme = (ROOT / "README.md").read_text().split("## Cost notes", 1)[1]
    for text in (readme, (ROOT / "DEPLOYMENT.md").read_text()):
        assert "reservation rather than a ceiling" in _prose(text)
        assert "worker limits" not in _prose(text)


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


def test_diagnostics_provenance_caveat_is_recorded():
    """resolve_dataset hands the callers a local path, so the URI is not recorded."""
    readme = _prose((ROOT / "README.md").read_text())
    assert "not the registry URI, is what a regenerated diagnostics asset" in readme
    assert _git_tracks(Path("data") / "spm_gap_diagnostics.json")
