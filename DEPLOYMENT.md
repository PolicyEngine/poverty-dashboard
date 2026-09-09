# Deployment

Two pieces: a Modal app (Python backend that runs simulations) and a Vercel app
(the Next.js dashboard).

## 1. Vercel — frontend first

For this upgrade-removal migration, deploy the frontend before the backend.
The existing frontend sends `upgrade=false` even for version reads. The new
backend rejects that obsolete query with HTTP 422, while the new frontend's
plain `/versions` request works with the existing backend. Keep the existing
backend serving until the frontend deployment is verified.

Use a Vercel project with **root directory set to `frontend/`**. Confirm its
existing `NEXT_PUBLIC_MODAL_BASE_URL` resolves to the serving backend, and keep
that value for the frontend rollout. `NEXT_PUBLIC_BASE_PATH` should remain blank
for a standalone deployment.

The live source inventory on September 9, 2026 confirmed
`https://poverty-dashboard.vercel.app` uses
`https://policyengine--poverty-dashboard-web-app.modal.run`. Reconfirm the actual
production aliases and compiled frontend backend URL at deployment time.

After deploying the frontend, read back the production deployment identity and
served JavaScript. Verify version requests contain no `upgrade` query and the
plain backend `/versions` and `/health` return HTTP 200. Verify the frontend's
recompute request builder sends only `year`; do not run a population recompute
as a deployment probe. Refresh existing dashboard tabs onto the new frontend
before switching the backend, since previously loaded JavaScript retains the
old query contract.

## 2. Modal — pinned backend

Only after the new frontend is serving, deploy from the repo root:

```bash
make install-python
uv run modal deploy modal_app.py
```

The backend exposes:

- `GET  /health`
- `GET  /baseline` — returns the JSON committed to the repo (only useful as a fallback)
- `GET  /versions` — installed wrapper, country, core, and SPM package versions
- `POST /recompute?year=2024|2025|2026` — fan out across regions, return fresh baseline JSON

Both local and Modal installations take their exact legacy wrapper/model/SPM
pins from `pyproject.toml`. Updating packages requires an image rebuild; requests
cannot install or upgrade packages. Unknown query options are rejected.
Per-region recompute responses retain returned `policyengine_bundle` provenance,
installed versions, and the applied `region_scope`.

Read back the deployed Modal version and serving URL. Verify `/health` returns
HTTP 200 and `/versions` reports wrapper 5.3.0, US 1.764.6, Core 3.30.1 and SPM
0.3.1. Verify `/versions?upgrade=false` now returns HTTP 422 without changing
the runtime, then verify plain `/versions` still returns the same package tuple.
Check requests from the newly served frontend succeed. Package or source changes
require another reviewed image build; requests never upgrade dependencies.

## 3. Numeric assets and rollback

The `prebuild` step copies `data/baseline.json` from the repo root into
`frontend/public/baseline.json` so the dashboard ships with the committed
numbers and loads instantly. To update the deployed numbers, recompute locally
(or via the Modal `/recompute` endpoint), commit the new `baseline.json`, and
Vercel will pick it up on the next push. Preserve the previous files separately
and verify all returned regions and provenance before replacing any assets.
Source and image updates alone do not regenerate the checked-in numeric data.

Retain both previous deployment identities before rollout. If only the frontend
has changed, it can be rolled back while the old backend still serves. Once the
strict backend is deployed, restore the previous backend first and verify it
accepts both plain `/versions` and `/versions?upgrade=false`; only then restore
the old frontend. Never roll the frontend back to its old query contract while
the strict backend is serving. Keep numeric assets at their reviewed versions
through either sequence.

## 4. Local development

```bash
cd frontend
npm install
npm run dev    # http://localhost:3010
```

For local computes without Modal:

```bash
uv run python -m poverty_dashboard.compute_local us      # federal only
uv run python -m poverty_dashboard.compute_local --year 2024 us
uv run python -m poverty_dashboard.compute_local --all   # all 52 regions (~30 min)
```
