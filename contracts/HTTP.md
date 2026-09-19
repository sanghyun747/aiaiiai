# Frozen HTTP and semantic contract — v1.0.0

Authority: v1.openapi.json. Do not change it from an executor branch. JSON field names are snake_case, times are RFC3339 with an explicit offset, and null means unavailable, not zero. UI labels/content are Korean.

## Transport

Frontend dev: http://127.0.0.1:5317. Backend: http://127.0.0.1:8317. A configures Vite to proxy /api and /p to 8317. Browser requests use relative paths. Only B owns backend CORS; allow exactly the approved frontend origin if direct requests are needed, never wildcard plus credentials.

A stores base URL configuration only in frontend/.env.example. B stores secrets only in ignored backend/.env; committed backend/.env.example contains empty placeholders. No root .env or root lockfile.

| Method/path | Request | Response |
|---|---|---|
| GET /api/v1/health | none | 200 Health; configured means key presence, NOT a successful remote call |
| POST /api/v1/runs | multipart profile_json + optional old_export/current_export; Idempotency-Key: fresh random UUID | 202 Accepted |
| GET /api/v1/runs/{run_id} | Authorization: Bearer access_token | 200 Run; poll every 1500ms, stop at succeeded/partial/failed |
| GET /api/v1/runs/{run_id}/artifacts/report.md | same per-run bearer token | 200 text/markdown; Content-Disposition attachment; fetch blob, then offer save |
| POST /api/v1/runs/{run_id}/publish | same bearer, PublishRequest JSON | 200 Publication; status distinguishes sandbox and public success |
| GET /p/{public_token} | unguessable public token created only by explicit publish | 200 sanitized text/html; otherwise 404 |

The browser must not manually set Content-Type for multipart FormData. Send profile_json as JSON.stringify(profile). Profile's decoded object must satisfy the Profile schema. Missing either member of an uploaded ZIP pair is 422; a single export never proves historical losses.

sample_followers=true means server-generated synthetic ZIPs and must reject simultaneous uploaded files. sample_followers=false with no ZIP pair means followers=null, not a zero-loss result. data_mode=demo chooses synthetic trend evidence; it does NOT request provider mocks. A real demo normally uses synthetic inputs through live Nosana and Daytona.

Real uploads require cloud_processing_consent=true AFTER the user is shown that minimized follower data is sent to Daytona, aggregate data to Nosana, and private result retention is local/operator-controlled in this MVP. Do not check that box for the user or infer approval from providing a local path. Public publishing requires separate consent. In deployed/public MVP use synthetic-only mode until private upload access, retention and authorization have passed inspection.

## Job behavior

A job is queued → running → succeeded/partial/failed. Stages: validate → plan → analyze → recommend → render → done. Stage changes reflect actual work, never timer-only fake progress. B uses one backend process with a bounded executor (at most two jobs); no Redis/Celery/DB requirement. Document jobs lost on process restart. Duplicate Idempotency-Key with identical payload reuses one run; a different payload returns 409. Treat this key as private and unpredictable, do not log it.

is_mock is true when ANY computation/provider response in this run was simulated. Mock sample fixtures are never presented as live. A previous real receipt replayed from cache has trace.mode=cached, not live. Provider failures preserve validated partial data and structured errors; no silent local/OpenAI/other-provider fallback presented as Nosana/Daytona.

succeeded requires result != null, exactly three validated actions, a verified generated report artifact and successful relevant Nosana and Daytona operations. It does NOT require DNSimple: publishing is a separate user action. partial may contain fewer actions and/or no artifact and must explain why. failed may contain no result. No success claims from an HTTP 202, a queued job, or a configured key alone.

Suggested application error codes: INVALID_PROFILE, INVALID_ZIP, ZIP_LIMIT_EXCEEDED, UNSUPPORTED_EXPORT, INCOMPLETE_EXPORT_PAIR, CONSENT_REQUIRED, IDEMPOTENCY_CONFLICT, NOT_FOUND, UNAUTHORIZED, JOB_LIMIT, PROVIDER_UNAVAILABLE, MODEL_UNAVAILABLE, AI_OUTPUT_INVALID, EVIDENCE_INVALID, ARTIFACT_NOT_READY, PUBLISH_APPROVAL_REQUIRED, DNS_NOT_CONFIGURED. HTTP mappings: 400 malformed, 401 token missing/wrong, 404 unknown run/artifact, 409 duplicate conflict/not ready, 413 size limit, 415 non-ZIP, 422 semantic validation/consent, 429 concurrency/rate limit, 503 remote prerequisite failure. Handle these with ErrorEnvelope; never expose exception stack, tokens, absolute paths or private rows in error messages.

## Source/AI constraints

All source IDs are unique and action/opportunity source_ids reference existing sources. Live/cached sources require a real source URL and observed_at; synthetic sources have source_mode=synthetic and must not invent live URLs. published_at may be null. UI opens valid external HTTPS source links only, with noopener/noreferrer.

A single observation only supports momentum_evidence=single_observation or insufficient. mean_views_per_hour, when present, is a deterministic descriptive average, not current growth speed, acceleration, a probability or an Instagram trend ranking. For any future measured_growth or measured_acceleration status, B must retain sufficient timestamped observations and show the computation; P0 should leave these statuses unused.

LLM output cannot manufacture follower counts, observations, sources, success probabilities, revenue, baseline or sponsorship eligibility. Sum(action.production_minutes) <= profile.weekly_minutes. An unknown baseline stays null and success_rule asks the user to collect a comparable baseline. Each action includes a distinct testable proposition; duplicate wording is not three experiments.

## Follower invariants

Reuse the source skill's deterministic diff. Add a separate mandatory audit layer and do not expose the source script's preliminary Markdown as a final report.

raw_missing_count = outside_window_count + renamed_still_following_count + relationship_absent_count + unresolved_count + explicitly_inactive_count.
old_count = retained_count + raw_missing_count. current_count = retained_count + raw_new_count. export_count_delta = current_count - old_count.
new_observed_excluding_renames = raw_new_count - renamed_still_following_count; label it newly observed handles, not proven new followers if export coverage is uncertain.

Every comparable-window candidate has an audit entry, including explicitly inactive candidates (they remain excluded). relationship_absent=true requires accepted current/manual evidence AND a resolved audit permitting absence. confirmed_rename_still_current_follower and username_change_not_ruled_out ALWAYS imply relationship_absent=false.

Timestamp-only rename linkage is a conservative rule inherited from the supplied skill, not a universal Instagram identity guarantee. Require consecutive exports explicitly asserted, at least one retained valid-timestamp pair, exact timestamp stability for ALL retained valid pairs, candidate timestamp unique in both FULL follower exports, and exactly one old-only/current-only pairing. No vacuous success with zero comparable retained records. Store evidence_method=export_continuity through Audit.method and qualify the UI as an export-continuity match. A collision/instability/nonconsecutive pair remains unresolved.

Without a positive stable-ID/public manual audit, a missing handle stays username_change_not_ruled_out. An indexed name, similar avatar/display name, HTTP 200 shell, unavailable profile or search absence is not an identity/active/deactivation proof. The demo fixture's synthetic audit applies ONLY to its own synthetic ZIPs; never apply it to real uploaded records. Do not let the normal browser client submit arbitrary 'verified' statuses.

## Report/publication constraints

Private run JSON may include audited usernames only behind its per-run token. Nosana requests contain no handles. Downloaded Markdown and public HTML are generated from an allowlist of aggregate statistics, source citations, actions and limitations, not by dumping raw JSON. Escape HTML; do not render arbitrary model HTML, scripts or raw markdown HTML.

DNSimple sandbox results have environment=sandbox, status=sandbox_record_created, public_url=null. Production remains dns_pending until the new record is verified, the actual hostname resolves, TLS is valid and the report route returns the intended sanitized content. A CNAME targets a hostname only, never a URL path. Existing records must not be overwritten or deleted. A record that conflicts with the expected target is an error requiring review.

fallback_url is only an already working app-origin /p/{public_token} URL after publication consent; no fabricated domain/URL. Local URLs must be labeled local-only. DNSimple failure must not break private report download. Do not implement purchase/registration or expose provider keys to A.

## Fixture interpretation

fixtures/run-sample.json is a fully typed UI example, intentionally is_mock=true with synthetic data. fixtures/follower-case.json describes a seven-to-six-handle synthetic case. B creates matching ZIPs in backend runtime test output and computes the result, never hardcodes production counts. It is not a live Instagram result and not a growth or loss claim about a real user.
