# PolicyEngine poverty dashboard

Internal dashboard tracking baseline federal and per-state poverty and child
poverty rates from PolicyEngine-US. Recomputations use the installed wrapper's
managed population and preserve its returned bundle provenance:

- Load the certified national population with
  `policyengine.us.managed_microsimulation`.
- For states, apply the registry's `state_fips` filter to person-level results.
- Map SPM-unit poverty variables to people, then use MicroSeries weighted
  operations for all, child, working-age, and senior poverty rates.

## Layout

```
modal_app.py              Modal FastAPI deployment with parallel_map fan-out
poverty_dashboard/        Python package for calculations and CLI tools
scripts/                  Compatibility wrappers for old module entry points
tests/                    Python unit tests
.github/workflows/ci.yml  Python and frontend CI
data/baseline.json        Committed baseline — frontend reads this on load
data/census_spm_2024.json Census/BLS SPM report benchmarks for comparison
data/spm_gap_diagnostics.json
                          PolicyEngine/Census diagnostic comparisons
frontend/                 Next.js + PE design system dashboard
```

## Install

```bash
make install
```

This creates a local Python 3.14 `.venv` with `uv`, installs the package in
editable mode with development tooling, and installs frontend dependencies.

## Deploy

```bash
make install-python
uv run --locked modal deploy modal_app.py
# copy the printed web_app URL into your env
export MODAL_BASE_URL=https://<...>.modal.run
export NEXT_PUBLIC_MODAL_BASE_URL=$MODAL_BASE_URL
```

## Recompute baseline (writes data/baseline.json)

```bash
uv run python -m poverty_dashboard.precompute_baseline
uv run python -m poverty_dashboard.precompute_baseline --year 2024
git add data/baseline.json && git commit -m "Refresh baseline"
```

To test a locally built national dataset, point the computation at the H5 file:

```bash
POVERTY_DASHBOARD_US_DATASET=/tmp/enhanced_cps_2024_post_989_cps_half_only.h5 \
  uv run python -m poverty_dashboard.compute_local --year 2024 us
```

## SPM element effects

The package can calculate Census Table B-6-style poverty impacts by
arithmetically removing each SPM resource or expense from baseline
`spm_unit_net_income`. This does not rerun a neutralized microsimulation, so it
does not include tax-benefit interactions.

```bash
uv run python -m poverty_dashboard.spm_elements --year 2024
poverty-dashboard-spm-elements --year 2024
uv run python -m poverty_dashboard.spm_diagnostics --year 2024
```

Federal refundable tax credits are mapped to federal EITC plus refundable CTC.
Federal income tax is mapped before refundable credits, because Census reports
refundable credits separately. State taxes are split into PE-only diagnostics
for state income tax before refundable credits and state refundable tax credits,
because Census Table B-6 does not publish those rows.

Child support received and workers' compensation are currently shown as upstream
SPM resource formula gaps: PolicyEngine has the inputs, but its SPM net income
does not yet include them. Utility assistance maps to PolicyEngine energy plus
broadband components (`spm_unit_energy_subsidy`, `acp`, and `ebb`), matching the
Census Table B-6 footnote that defines utility assistance as ACP plus other
noncash energy benefits.

The diagnostics also include candidate administrative calibration targets. For
child support, received and paid amounts should share the same gross-flow target,
with net child support retained as received minus paid. For workers'
compensation, NASI's latest state summaries currently end in 2022; the first
2024 target should use cash benefits and an indemnity-severity uprating rather
than total benefits including medical payments.

## Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:3010
```

## Checks

```bash
make check
```

GitHub Actions runs the same Python checks (`ruff format --check`,
`ruff check`, `pytest`) and frontend checks (`npm run typecheck`,
`npm run build`) on pushes to `main` and pull requests.

The dashboard:

1. Loads the committed `data/baseline.json` instantly.
2. Shows the package versions that produced those numbers.
3. Shows Census 2024 SPM report benchmarks next to PolicyEngine results.
4. Compares Census Table B-6 element effects with PolicyEngine arithmetic
   element effects.
5. Lets you select 2024, 2025, or 2026 before recomputing.
6. "Check deployment" calls `/versions` on the Modal app and compares its
   installed packages with the versions recorded in the displayed baseline.
7. "Recompute" runs `compute_region_remote.starmap` over
   the national and 51 state regions; the result is shown in-app and offered as
   a JSON download for you to commit.

Runtime packages are pinned in `pyproject.toml`, and `uv.lock` fixes the full
dependency resolution used by CI and the Modal image. Package changes require
a reviewed lock update, rebuild and deployment. Current
pins protect the existing legacy SPM bundle; publication of a new SPM package
does not update this deployment or the checked-in numbers.

The diagnostic scripts still contain historical raw-CPS comparisons and require
a separate source/provenance migration before canonical asset regeneration. See
[DEPLOYMENT.md](DEPLOYMENT.md) for the remaining work and deployment gates.

## Cost notes

`compute_region_remote` runs 51 containers in parallel via Modal's `starmap`.
Each container takes a few minutes (cold start + dataset download + sim), so
expect roughly 51 × a few CPU-minutes per recompute. Don't wire this to a cron.
