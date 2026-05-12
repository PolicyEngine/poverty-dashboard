# Deployment

Two pieces: a Modal app (Python backend that runs simulations) and a Vercel app
(the Next.js dashboard).

## 1. Modal — backend

Deploy from the repo root:

```bash
pip install -e .
modal deploy modal_app.py
```

Modal will print a `web_app` URL like `https://policyengine--poverty-dashboard-web-app.modal.run`.
Save that — Vercel needs it.

The backend exposes:

- `GET  /health`
- `GET  /baseline` — returns the JSON committed to the repo (only useful as a fallback)
- `GET  /versions?upgrade=true|false` — installed PolicyEngine package versions
- `POST /recompute?upgrade=true|false` — fan out across 51 regions, return fresh baseline JSON

## 2. Vercel — frontend

Create a Vercel project with **root directory set to `frontend/`**.

Environment variables:

- `NEXT_PUBLIC_MODAL_BASE_URL` — the Modal URL from step 1.
- `NEXT_PUBLIC_BASE_PATH` — leave blank for a standalone deployment.

The `prebuild` step copies `data/baseline.json` from the repo root into
`frontend/public/baseline.json` so the dashboard ships with the committed
numbers and loads instantly. To update the deployed numbers, recompute locally
(or via the Modal `/recompute` endpoint), commit the new `baseline.json`, and
Vercel will pick it up on the next push.

## 3. Local development

```bash
cd frontend
npm install
npm run dev    # http://localhost:3010
```

For local computes without Modal:

```bash
python -m scripts.compute_local us              # federal only
python -m scripts.compute_local --all           # all 52 regions (~30 min)
```
