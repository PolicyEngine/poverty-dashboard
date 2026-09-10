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
uv run --locked modal deploy modal_app.py
```

The backend exposes:

- `GET  /health`
- `GET  /baseline` — returns the JSON committed to the repo (only useful as a fallback)
- `GET  /versions` — installed wrapper, country, core, and SPM package versions
- `POST /recompute?year=2024|2025|2026` — fan out across regions, return fresh baseline JSON

Both local and Modal installations use the committed `uv.lock`, preserving
the exact legacy wrapper/model/SPM pins in `pyproject.toml` and the resolved
transitive dependencies. The Modal image uses `Image.uv_sync` with uv 0.11.7
and `--locked --no-dev`; missing or stale locks fail the build. The dashboard
source is copied separately after dependency installation. Local development
and CI also install the `dev` extra from that lock. Updating packages requires
a reviewed lock update and image rebuild; requests cannot install or upgrade
packages. Unknown query options are rejected.
Per-region recompute responses retain returned `policyengine_bundle` provenance,
installed versions, and the applied `region_scope`.

Read back the deployed Modal version and serving URL. Verify `/health` returns
HTTP 200 and `/versions` reports the exact, non-null tuple: wrapper 5.3.0,
US 1.764.6, Core 3.30.1 and SPM 0.3.1. Verify `/versions?upgrade=false` now returns
HTTP 422 without changing the runtime, then verify plain `/versions` still
returns the same package tuple.
Check requests from the newly served frontend succeed. Package or source changes
require another reviewed image build; requests never upgrade dependencies.

Before production, verify an actual staged Modal image: record its source and
lock hashes, Python/platform identity, complete installed distribution versions
and package-file hashes against the lock's applicable Linux artifacts. Record
Modal's runtime-injected packages separately. Check the serving contract above
on that staged image, without a population recompute. Record `sys.executable`,
`sys.prefix` and `/.uv/.venv/pyvenv.cfg` from the serving container and a
lightweight child launched through `sys.executable`, proving both use the locked
environment. Local recipe tests and a four-package `/versions` response do not
prove the full deployed closure.

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

### Private serving-process audit

Serving closure must be observed separately for `web_app`, `get_versions_remote`
and `compute_region_remote`. Container exec starts another process and cannot
establish these functions' actual Python prefixes.

For the existing public `web_app`, `/runtime-audit?nonce=<nonce>` is disabled (404)
without a server-only `POVERTY_RUNTIME_AUDIT_TOKEN`. During an explicitly approved
staged deployment, the operator may set the deployment-only
`POVERTY_RUNTIME_AUDIT_SECRET_NAME` to an existing Modal Secret containing that key.
Only `web_app` receives this optional Secret. No token belongs in frontend code,
URLs, source, logs or receipts. Send it in an `Authorization: Bearer ...` header;
missing or incorrect authentication returns 404 before metadata capture. The
route is omitted from OpenAPI and successful responses use `Cache-Control: no-store`.
This route observes the gateway itself and does not call any worker.

Use authenticated native Modal RPC to call the existing worker functions with a
fresh nonce, for example after resolving the actual deployed app/environment:

```python
compute = modal.Function.from_name(actual_app, "compute_region_remote",
                                   environment_name=actual_environment)
witness = compute.remote("us", runtime_audit_nonce=fresh_nonce)
versions = modal.Function.from_name(actual_app, "get_versions_remote",
                                    environment_name=actual_environment)
version_witness = versions.remote(runtime_audit_nonce=another_fresh_nonce)
```

The optional argument returns metadata before the calculation subprocess or version
lookup. Public `/versions` and `/recompute` reject this argument. All audit nonces
must contain 16–128 letters, digits, `_` or `-`. Normal calls retain the existing
calculation command, installed-version response and pinned scientific closure.

Bind each actual authenticated witness, PID, call/input IDs and nonce to the public
Modal call graph and the actual deployed app/function/image/task/source receipts.
The witness includes the serving interpreter/prefix, sanitized `pyvenv.cfg`
fields/hash, loaded module origins and a real lightweight child through
`sys.executable`. The child is not a population calculation. Full Linux wheel,
RECORD and source closure still require a separately authenticated capture from
the same container; missing correlation is a failed qualification component.
These hooks do not waive staged checks, frontend-first/backend-second promotion,
or backend-first rollback. No credential provisioning or deployment is implied by
this source change.

The witness reports whether both public Modal context IDs are present; this is
an observation, not identity approval. Null parent module origins mean the module
has not been loaded in that process. The lightweight child separately reports
installed package versions through metadata and its import paths, without
importing any model. Audit capture failures return generic uncached 502 JSON.
