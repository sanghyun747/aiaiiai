> **Status 2026-09-19:** Daytona analyze = LIVE. Nosana `plan` = LIVE and verified
> (`json_object` mode, receipt `chatcmpl-a96bd4e3bd7347a9`). Nosana `recommend` and the
> Daytona `render` stage are **still unproven live** — no artifact SHA-256 table exists yet.
> Opt-in labelled demo replay: `TRENDPILOT_LIVE_PROVIDERS=0` (fixture actions, `is_mock=true`,
> Daytona still real). Minimal UI at `GET /`. Missing keys: `DNSIMPLE_*`, `YOUTUBE_API_KEY`.

# TrendPilot backend (Session B)

Contract 1.1.0. Owns `backend/**` only.

## Setup

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # fill in keys; chmod 600; never commit
```

## Run

```bash
cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8317
```

Frontend dev origin `http://127.0.0.1:5317` is the only allowed CORS origin (no credentials).

## Test

```bash
cd backend && .venv/bin/python -m pytest -q tests
TRENDPILOT_LIVE_TEST=1 .venv/bin/python -m pytest -q tests -k live   # optional, hits real Nosana
```

Tests run offline with stubs. `TRENDPILOT_LIVE_PROVIDERS=0` makes runs fail fast instead of calling providers.

## Smoke

```bash
curl -s 127.0.0.1:8317/api/v1/health
curl -s -X POST 127.0.0.1:8317/api/v1/runs \
  -H "Idempotency-Key: $(uuidgen)" \
  -F "profile_json=$(cat ../fixtures/profile-sample.json)"
curl -s -H "Authorization: Bearer $TOKEN" 127.0.0.1:8317/api/v1/runs/$RUN_ID
```

Jobs are in-memory and process-local: **all runs are lost on restart.** Synthetic exports and
downloaded artifacts are retained under `backend/.runtime/<run-id>/` (gitignored, never auto-deleted).
