.PHONY: install install-python install-frontend format lint test check deploy recompute recompute-upgrade dev

install: install-python install-frontend

install-python:
	uv venv --python 3.14
	uv pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

format:
	uv run ruff format .

lint:
	uv run ruff check .

test:
	uv run pytest

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run pytest
	cd frontend && npm audit --audit-level=moderate
	cd frontend && npm run typecheck
	cd frontend && npm run build

deploy:
	uv run modal deploy modal_app.py

recompute:
	uv run python -m poverty_dashboard.precompute_baseline

recompute-upgrade:
	uv run python -m poverty_dashboard.precompute_baseline --upgrade

dev:
	cd frontend && npm run dev
