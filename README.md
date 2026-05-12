# PolicyEngine poverty dashboard

Internal dashboard tracking baseline federal and per-state poverty and child
poverty rates from PolicyEngine-US. Mirrors the dataset selection and poverty
calculation methodology used by `policyengine-api`'s `economy_service` /
`compare.py`:

- For each region, resolve the dataset via
  `policyengine.countries.us.regions.us_region_registry` (national →
  `enhanced_cps_2024.h5`, state → `states/{XX}.h5`).
- Run `policyengine_us.Microsimulation` against that dataset.
- Compute weighted means of `person_in_poverty` and `person_in_deep_poverty`,
  filtering `age < 18` for the child-poverty rate.

## Layout

```
modal_app.py              Modal FastAPI deployment with parallel_map fan-out
scripts/poverty_calc.py   Single-region calculation (the methodology)
scripts/regions.py        51 state region codes + national
scripts/precompute_baseline.py   CLI: hit /recompute, write data/baseline.json
data/baseline.json        Committed baseline — frontend reads this on load
frontend/                 Next.js + PE design system dashboard
```

## Deploy

```bash
pip install -e .
modal deploy modal_app.py
# copy the printed web_app URL into your env
export MODAL_BASE_URL=https://<...>.modal.run
export NEXT_PUBLIC_MODAL_BASE_URL=$MODAL_BASE_URL
```

## Recompute baseline (writes data/baseline.json)

```bash
python -m scripts.precompute_baseline                # use installed versions
python -m scripts.precompute_baseline --upgrade      # pip install -U first
git add data/baseline.json && git commit -m "Refresh baseline"
```

## Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:3010
```

The dashboard:

1. Loads the committed `data/baseline.json` instantly.
2. Shows the package versions that produced those numbers.
3. "Check latest" calls `/versions` on the Modal app and flags any package that
   has a newer version on PyPI than the committed baseline used.
4. "Recompute" / "Upgrade & recompute" runs `compute_region_remote.starmap` over
   the 51 regions; the result is shown in-app and offered as a JSON download
   for you to commit.

## Cost notes

`compute_region_remote` runs 51 containers in parallel via Modal's `starmap`.
Each container takes a few minutes (cold start + dataset download + sim), so
expect roughly 51 × a few CPU-minutes per recompute. Don't wire this to a cron.
