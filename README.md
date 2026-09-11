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

A recompute materializes the certified population into `data/` beside the
committed JSON assets. Those files are gitignored, so stage `data/baseline.json`
by name rather than `git add data`.

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
Their national population is the wrapper's sha256-verified local file, because
policyengine-core downloads with `repo_type="model"` and so cannot fetch the
registry's dataset-type Hugging Face repository.

## Cost notes

`/recompute` fans out all 52 regions — the nation and 51 states — through
`compute_region_remote.starmap`. Every region runs its own subprocess that
materializes and simulates the full certified national population: a state
result is the national person-level result masked by `state_fips`, not a
per-state dataset. One recompute is therefore 52 national-size simulations and
52 sha256 verifications of the national file. `max_containers` is unset, so
Modal decides the container count and it is not one per region; a container
that already holds the file does not download it again, which makes 52 the
upper bound on downloads rather than the count. `compute_local --all` runs the
same 52 national-size simulations serially in one process. Don't wire either to
a cron.

`compute_region_remote` asks for cpu 2.0 and 8192 MiB, `web_app` for cpu 1.0 and
2048 MiB. Modal turns a scalar `cpu`/`memory` into a reservation rather than a
ceiling, so neither number caps what a container may consume; the hard limits
are the 1200 s worker timeout and the 2400 s `web_app` request timeout. All four
values are unchanged from before every region became a national-size run, and
have not been measured against the certified population. Validate them on a
staged image before the first paid regeneration.
