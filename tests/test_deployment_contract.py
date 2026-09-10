"""Inspect actual Modal build instructions without building an image."""

from __future__ import annotations

import importlib.util
import re
import shlex
from pathlib import Path

from modal.image import _Image

ROOT = Path(__file__).resolve().parents[1]


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


def test_protection_document_link_resolves():
    readme = (ROOT / "README.md").read_text()
    paragraph = readme.split("The diagnostic scripts", 1)[1].split("\n\n", 1)[0]
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", paragraph)
    assert links, "Protection guidance must link to a checked-in document"
    assert all((ROOT / link).is_file() for link in links)
