## Verified replay-mode run with live Daytona render (2026-09-19 16:18 KST)

`TRENDPILOT_LIVE_PROVIDERS=0` → run `run_fdc9d8034fef20be` → **status `succeeded`**, `is_mock=true` (plan/recommend replayed from `fixtures/run-sample.json`, trace mode `mock`).
Daytona stages were **live**: sandbox `fa7889ff-8f4e-49e0-85f2-7ba591c9f1f4` — analyze (success), render (success), sandbox_stop (success). All 7 artifacts were downloaded through the API and re-hashed locally; every hash matches the value listed in `result.artifacts`.

| artifact | bytes | SHA-256 | matches listing |
|---|---|---|---|
| `content-strategy.json` | 20556 | `d720446bc38a627774ae3c0633eab35248fa541a13e0b4b56baa1e756329a9bd` | yes |
| `editing-guide.md` | 1594 | `db93d56af725488619944538cd77c0424df5e847c7bd7ea7824091838dd13d81` | yes |
| `publishing-package.md` | 1910 | `e758c270508d7aa4bea26163e9cf749fe95bda736cf75dd70c4bad57b9336219` | yes |
| `report.md` | 12375 | `2b8a7657204f2ba94a62edc05ef418a6c6acd4dcc4f494ba0a94160d3fe35c34` | yes |
| `script.md` | 2172 | `c288ba2902c3f8ecf97d30dd18da8b9d777d5fa5dedbdfdc5e338078ea39a47c` | yes |
| `shot-list.json` | 2970 | `477d899c0c2670e8b759073b139bbddf1d139e8a039e1de48d04288aab8369aa` | yes |
| `thumbnail-plan.md` | 1452 | `63feebe102fe7d73d3361e0a9987e1a9dc808801482c3f1ad50b58d44b5b4be2` | yes |

Contract note: replay trace entries use `mode="mock"` (the frozen contract allows only live/mock/cached); the run carries `is_mock=true` and a `sample_notice`.

# Session B handoff — backend, contract 1.1.0

## UPDATE 2026-09-19 (fixer session, 25-min budget) — read this before the older text below

1. **Nosana `plan` is UNBLOCKED and verified live.** `providers/nosana.complete_json` now sends
   `response_format={"type":"json_object"}` first and retries without it only if the endpoint
   rejects that parameter; enforces `MIN_MAX_TOKENS=4000` (a small budget makes qwen3 return
   `content: null` and spend everything on `reasoning`); reads `message.content` and falls back to
   `reasoning_content`/`reasoning`; strips `<think>…</think>` and code fences; extracts the first
   balanced `{…}`/`[…]` by string-aware brace counting; and on any parse failure dumps
   `text[:2000]` to `backend/.runtime/nosana_last_raw.txt` and reports the excerpt in the error.
   All prompts now end with the single English line
   `Return ONLY one JSON object. No prose, no markdown, no reasoning.`
   **Live receipt:** `chatcmpl-a96bd4e3bd7347a9`, model `qwen/qwen3.8-27b`, `json_mode=true`,
   usage `prompt=655 completion=1179 total=1834`, 14.1 s — parsed plan JSON returned.
   In-run receipt on `run_1dd3174d247e4e98`: `nosana plan live success`,
   usage `prompt=765 completion=1697 total=2462`.
2. **`recommend` is NOT yet confirmed live.** Run `run_1dd3174d247e4e98` was still in
   `running/recommend` when this session's hard stop hit. The 14 000-token production-package
   generation takes minutes on this endpoint. **No artifact SHA-256 table can be reported from a
   live run yet** — `render` has still never executed against Daytona for real. Saying otherwise
   would be fabricated. Next session: re-poll that run (process was killed, so re-submit) or use
   the replay path below to reach `render`.
3. **Labelled demo-replay path added (opt-in only).** `TRENDPILOT_LIVE_PROVIDERS=0` →
   `config.replay_mode_enabled()` → plan/recommend come from `fixtures/run-sample.json`,
   `run.is_mock=true`, `sample_notice=config.REPLAY_NOTICE`, extra limitation
   `worker.REPLAY_LIMITATION`, trace `mode="replay"`. **Daytona analyze AND render still run live.**
   Any other value of the env var (`""`, `"false"`, `"2"`) enables neither live nor replay, and a
   live provider failure never falls back — both are covered by tests.
4. **Minimal UI at `GET /`** → `backend/app/static/index.html` (plain HTML+JS, no build, light
   theme, one accent). Form → `POST /api/v1/runs` multipart with a fresh random `Idempotency-Key`;
   polls `GET /api/v1/runs/{id}` every 1500 ms; shows stage, the provider-trace table and a
   **MOCK/REPLAY** vs **LIVE** badge from `is_mock`; renders `strategy_mode`, `weakness_target` and
   all 5 production-package sections; artifact buttons use an authenticated `fetch` with the bearer
   in the header and a blob download (token never in a URL). **Not yet E2E-verified in a browser** —
   the route was added after the live run started and uvicorn was not restarted before the stop.
5. **Tests: `89 passed, 1 skipped`** (`backend/.venv/bin/python -m pytest -q`). New files:
   `tests/test_json_extraction.py` (20 tests: think-block/fence stripping, braces inside strings,
   escaped quotes, array-vs-object ordering, raw dump, json_object fallback, max_tokens floor,
   truncation) and `tests/test_replay.py` (13 tests incl. the no-silent-fallback guarantee).
   The 1 skip is still the optional live Nosana test. uvicorn on 8317 was killed before finishing.

### Still failing / missing
- `recommend` + `render` live end-to-end: unproven. No 7-artifact SHA-256 table exists yet.
- `DNSIMPLE_*` and `YOUTUBE_API_KEY` absent → publish `not_configured`, evidence `synthetic`.
- UI browser E2E (playwright screenshot) not run.


Branch `feat/backend` (from `main` @ 62e6068). **Not pushed.** Nothing outside `backend/**` was touched.

## What is REAL vs not — read this first

| Piece | State |
|---|---|
| FastAPI app, all 7 contract routes | REAL, running, covered by tests |
| Follower diff + audit (clean-room) | REAL, deterministic, matches `fixtures/follower-case.json` exactly |
| Daytona sandbox execution | **REAL, live** — sandbox created, analyzer uploaded, executed, JSON downloaded, hash recorded |
| Nosana inference | **PARTIAL / BLOCKED** — auth, `/v1/models` and a plain chat completion all work live, but the `plan` stage output could not be parsed into JSON in 3 attempts. Every run ended `failed` with the real error recorded. No fake success anywhere. |
| Artifact rendering in sandbox | code complete, **never executed end-to-end** because the run fails before `render` |
| DNSimple | adapter + 3 stub tests; `configured=false`; publish returns `not_configured`, never `sandbox_record_created` |
| YouTube | adapter written; no API key → synthetic sources, `source_mode=synthetic`, `evidence_mode=synthetic`, trace `mode=mock status=skipped` |

## Commits

- `05f28a1` backend: FastAPI contract 1.1.0 routes, clean-room follower analyzer, Nosana/Daytona/DNSimple adapters
- (this commit) tests, JSON-extraction hardening, README/HANDOFF

Files: `app/{main,models,config,store,pipeline,worker,prompts,exports,report_html}.py`,
`app/sandbox/render_artifacts.py`, `providers/{nosana,daytona_sandbox,dnsimple,youtube,errors}.py`,
`vendor/follower_diff/analyzer.py`, `vendor/PROVENANCE.md`, `tests/{conftest,test_api,test_actions,test_followers,test_exports}.py`,
`requirements.txt`, `.gitignore`, `.env.example`, `README.md`, `HANDOFF.md`.

## Tests

```
cd backend && .venv/bin/python -m pytest -q tests
56 passed, 1 skipped, 1 warning in 0.32s
```

The 1 skip is the optional live Nosana test (`TRENDPILOT_LIVE_TEST=1`). Offline by default, providers stubbed.

Coverage: contract shapes; exactly 3 actions; safe_bet + growth_experiment presence; weakness_target
required for growth and cleared for safe_bet; full production package; shot-list order 1..n; weekly
time budget; unknown source id rejected; model cannot invent a baseline; follower invariants +
negatives (nonconsecutive pair, unstable retained timestamps, timestamp collision, rename never
implies absence, absence requires current evidence, fixture audit never applied to a user upload);
malformed/traversal/corrupt ZIP; idempotency reuse + 409 conflict; per-run bearer auth incl.
cross-run token rejection; artifact allowlist + traversal; SHA-256 mismatch → 409; public report
privacy (no handles, no token, escaped model text); DNSimple not-configured, URL-target refusal,
stub create+readback, conflicting-record error; provider failure → `failed` with real error;
AI output invalid after exactly one repair → `partial`.

## The REAL end-to-end run (live server on 8317)

```
POST /api/v1/runs  (profile-sample.json, sample_followers=true, fresh Idempotency-Key) -> 202
run_id run_26724f04b9468eec   (latest of 3 attempts: run_0f145b724f601794, run_7e9fb8b502d52c1e)
poll -> running/plan ... -> failed/done
```

Terminal run JSON (trimmed, real):

```json
{"status":"failed","stage":"done","is_mock":false,
 "error":{"code":"PROVIDER_UNAVAILABLE",
          "message":"ValueError: unterminated JSON in model output","retryable":false},
 "trace":[
  {"provider":"youtube","operation":"search","mode":"mock","status":"skipped",
   "detail":"YOUTUBE_API_KEY 미설정. 합성 근거를 사용하며 실시간 수집이 아닙니다."},
  {"provider":"daytona","operation":"analyze","mode":"live","status":"success",
   "remote_id":"2c74045d-f5c2-495c-ad54-475c47319d7c","duration_ms":571,
   "artifact_sha256":"ab012808f2adae463f5302f5e7dc1fb661222ac49b9a0d1a9bb78af046f32a9c"},
  {"provider":"daytona","operation":"sandbox_stop","mode":"live","status":"success",
   "remote_id":"2c74045d-f5c2-495c-ad54-475c47319d7c","detail":"sandbox deleted"}]}
```

**Daytona sandbox id: `2c74045d-f5c2-495c-ad54-475c47319d7c`** (deleted at the end of the run).
Downloaded `followers.json` SHA-256 `ab012808f2adae463f5302f5e7dc1fb661222ac49b9a0d1a9bb78af046f32a9c`,
invariants re-verified locally after download.

**No artifact list and no SHA-256 table can be reported, because `render` never ran.** Saying
otherwise would be a fabricated sponsor result. `report.md` was therefore never downloaded from a
live run; the download path itself is exercised by `test_report_download_is_attachment`
(Content-Disposition attachment + SHA-256 match).

### Nosana blocker (exact)

- Base URL `https://inference.nosana.com/v1`, bearer key present and accepted.
- `GET /v1/models` → `nvidia/nemotron-3-embed-1b` (embedding, excluded), `qwen/qwen3.8-27b` (selected).
- A trivial completion works: `finish_reason=stop`, content `\n\n{"ok":true}`, usage
  `prompt_tokens=62 completion_tokens=40 total_tokens=102`. **That is the only verified Nosana receipt.**
- On the real `plan` prompt the response body never yielded parseable JSON. Fixes applied and still
  failing: `max_tokens` 1500→4000 (plan) / 8000→14000 (recommend); `finish_reason=="length"` now
  raises `AI_OUTPUT_INVALID`; extraction now strips `<think>` blocks and code fences and scans every
  candidate start for a balanced value. The last live attempt still reported the pre-patch message,
  which was not re-verified before the deadline — **the next session must re-run and log the raw
  model text** (add a debug dump of `text[:2000]` in `providers/nosana.complete_json`).
- Likely causes, untested: the model emits a reasoning preamble with unbalanced braces, or the
  Korean prompt pushes it into prose. Cheapest next step: ask for JSON in a single-line English
  instruction, or use `response_format={"type":"json_object"}` if the endpoint supports it.

## Missing keys / blockers

- `DNSIMPLE_API_TOKEN` / `DNSIMPLE_ACCOUNT_ID` / `DNSIMPLE_ZONE`: absent on this machine. Sandbox
  record creation is therefore unproven. `health.configured.dnsimple=false`; publish → `not_configured`.
- `YOUTUBE_API_KEY`: absent. All evidence is synthetic and labelled as such.
- Original skill `C:\Users\sangh\SKILL\instagram-follower-diff` is on the teammate's Windows box and
  was never read here → `vendor/follower_diff/analyzer.py` is a **clean-room reimplementation**; see
  `vendor/PROVENANCE.md` for the replacement procedure. No original path SHA-256 exists.
- `docs/verify_prep.py` was not run (not present in this clone).
- Frontend integration not yet exercised; Session A has not created a run against this server.
  **MVP is NOT complete.**

## Security / retention

- Secrets live only in `backend/.env` (chmod 600, gitignored). `backend/.env.example` holds empty
  placeholders. No secret value was printed or committed.
- Nosana receives anonymised aggregates + allowed source ids only — no usernames, no fbid, no ZIPs.
- Daytona receives minimized `{username,timestamp}` synthetic records only. Real uploads require
  `cloud_processing_consent=true`; the server never infers it.
- Per-run bearer tokens (32B urlsafe), constant-time compare; Idempotency-Key is never logged.
- Public `/p/{token}` is allowlisted aggregates, fully escaped, `CSP default-src 'none'`, noindex.
- Retained (NOT deleted, per policy): `backend/.runtime/run_26724f04b9468eec`,
  `run_0f145b724f601794`, `run_7e9fb8b502d52c1e` (synthetic ZIPs + analysis input),
  `run_stub_fail`, `run_stub_invalid`, `uploads/`, `uvicorn.log`, `uvicorn.pid`.
- Leftover processes: **none** — the uvicorn on 8317 was killed before finishing. Daytona sandboxes
  created by runs were deleted by the run's own `finally` block (trace `sandbox_stop: deleted`).
