# Provider implementation and acceptance gates

Checked official documentation on 2026-09-19. No provider keys, credits, connectivity or app execution have been verified in this preparation session. This is an implementation specification, not a completion report.

## Architecture and prerequisites

React/TypeScript/Vite in frontend; Python/FastAPI in backend. One bounded in-memory job runner (one process, at most two jobs); no vector DB, Redis, training, fine-tuning or agent framework. Use and pin currently tested dependency versions. Preserve the Python comparator instead of translating it.

Flow: API validates input -> Nosana allowlisted plan -> Daytona fixed-code analysis -> Nosana evidence-grounded experiment JSON -> Daytona fixed-template Markdown -> API schema/semantic validation -> UI. Acquire public source data in parallel with follower processing where possible. DNSimple publication is separate from the core analysis path.

Preparation found no DAYTONA_API_KEY, NOSANA_API_KEY, DNSIMPLE_TOKEN or YOUTUBE_API_KEY in the current DevSpace process environment. Keys may exist elsewhere; do not scan credentials, browser profiles, unrelated .env files or password stores. Provide backend/.env.example with empty placeholders. Ask the user to populate secrets locally, not in chat.

Environment names: DAYTONA_API_KEY, NOSANA_API_KEY, NOSANA_BASE_URL, NOSANA_MODEL, DNSIMPLE_TOKEN, DNSIMPLE_ACCOUNT_ID, DNSIMPLE_ZONE, DNSIMPLE_MODE, DNSIMPLE_TARGET_HOST, PUBLIC_APP_ORIGIN, YOUTUBE_API_KEY, ALLOW_REAL_UPLOADS, ALLOW_PRODUCTION_DNS. Both ALLOW flags default false. Never send credentials to frontend, Daytona worker code, Git or logs. Frontend VITE_* variables are public.

## Nosana

Official: https://learn.nosana.com/api/llm.html

Base URL https://inference.nosana.com/v1; Authorization: Bearer <NOSANA_API_KEY>. GET /models to identify a currently served model, then POST /chat/completions. Use httpx or a compatible client. Do not hardcode a tutorial model; availability is dynamic. Confirm credits and a small inference before integration. Per-token billing uses Nosana credits.

Plan input contains creator-declared topic, goal, time and allowed task metadata. Recommendation input contains sanitized public source records/IDs and aggregate follower counts. No usernames, fbid, ZIPs, private audit details, run tokens or credentials. External titles are quoted untrusted data, never instructions. Model output is JSON selecting fixed tasks or providing actions; never executable code/shell/URLs to fetch.

Do not assume the selected model supports tool calling or response_format/json_schema; test before enabling. Parse final message.content, not reasoning. Validate with Pydantic/JSON Schema AND semantic invariants. At most one bounded repair; no invented facts. Model cannot overwrite deterministic counts, audit statuses, URLs, traces or hashes. Every experiment cites supplied source IDs and respects the time budget. No success probability, forecast income or causality for individual unfollows.

Record model, actual provider/request ID when present, response hash, elapsed time and usage when returned. Missing IDs stay null. Do not fabricate receipts. Suggested timeout caps: plan 15s, recommendations 35s, repair 15s; run deadline 120s. Tune from real measurements; these are limits, not latency promises. Error/credit/model failures are visible partial/failed states, never a hidden provider substitution.

## Daytona

Official: https://www.daytona.io/docs/en/python-sdk/
Files: https://www.daytona.io/docs/en/file-system-operations/
Execution: https://www.daytona.io/docs/en/process-code-execution/

Use official Python SDK. Check installed SDK signatures for Daytona/DaytonaConfig, create, fs upload/download, process execution and stop. Run a synthetic smoke test first. Do not invent arguments from memory.

Daytona must actually execute deterministic follower analysis and generate Markdown from a fixed template. Download the output, hash it, record sandbox ID, exit code and duration. A hello-world-only call or locally generated report is not full integration. No free-form model-generated code, arbitrary shell or arbitrary package installation.

Real source ZIPs stay unchanged/unextracted locally. Before any real user-data upload require both operator ALLOW_REAL_UPLOADS and explicit user consent. Default/public demo uses synthetic-only input. Upload only minimized relevant validated records; never unrelated messages, contacts, cookies or export members. Do not upload source ZIPs wholesale.

ZIP validation starting limits: compressed 25 MiB each, <=200 members, per JSON 20 MiB uncompressed, total 100 MiB uncompressed, compression ratio <=200. Enforce streaming byte limits; metadata alone is not enough. Reject encrypted entries, symlinks, unsafe paths, malformed JSON and invalid timestamp ranges. Whitelist only followers_*.json, following.json and recently_unfollowed_profiles.json under the expected connections directory. Never extractall. Missing optional active evidence -> unresolved/warning, not invented activity. Missing usable current follower timestamps -> controlled error.

Retain source behavior in a copied vendor module, then add audit logic in the wrapper. The source code's old 'Final candidates' wording is preliminary and must NOT be served directly as final UI/report. Timestamp linkage is the supplied skill's heuristic, not a provider-guaranteed stable account ID; qualify that limitation even when the rule passes.

Stop owned sandboxes on success/failure when supported. Do not delete files, retained sandbox data, worktrees or test outputs without user approval. Disable automatic deletion where possible and verify lifecycle configuration; otherwise disclose retention limits before private-data use. Record retained sandbox IDs and potential storage retention/charges. No always-on sandbox web server needed.

## YouTube evidence

Official: https://developers.google.com/youtube/v3/docs/search/list
Statistics: https://developers.google.com/youtube/v3/docs/videos/list

Backend uses search.list(part=snippet,type=video,q=query,publishedAfter=7_days_ago,order=date,maxResults=15,regionCode=KR,relevanceLanguage=ko), followed by videos.list(part=snippet,statistics,contentDetails,id=...). Use official APIs, bounded calls and actual observation timestamps. This is a recent search sample, not exhaustive trends. RegionCode is availability context, not proof of creator nationality. Duration alone does not prove Shorts; metadata is not proof the video was watched.

Mean views/hour is views divided by positive hours since publication. Label as a descriptive average, NOT instantaneous growth/acceleration. One snapshot cannot prove momentum. Preserve platform and source URL; YouTube evidence is not Instagram-specific trend proof. Missing values remain null. Cache only genuinely collected observations with time/provenance. If live acquisition fails, show a failure or an explicitly labeled cached/synthetic mode; never silently substitute invented live data.

## DNSimple

Official: https://developer.dnsimple.com/v2/zones/records/
Sandbox: https://developer.dnsimple.com/sandbox/

Sandbox base https://api.sandbox.dnsimple.com/v2; production https://api.dnsimple.com/v2; Bearer auth. Sandbox uses a separate account/token/zone from production. Read exact existing record, POST a new record to /{account}/zones/{zone}/records, then GET the returned ID to verify. Reuse identical records; stop on conflicting content. Never overwrite/delete existing records or buy/register domains.

Minimum integration: explicit publish action creates/read-verifies a unique sandbox CNAME to configured DNSIMPLE_TARGET_HOST. Return sandbox_record_created and public_url=null. If no test zone or target exists return not_configured. Sandbox API execution is real integration with a test environment, NOT real public DNS/hosting.

Production URL is P1 until an owned delegated zone, approved new alias, working hosting and TLS/host routing exist. Prefer reports.<owned-zone> plus /p/<unguessable-public-token>, not per-run certificate provisioning. CNAME targets a hostname, not a path. Return dns_pending until DNS resolution, valid HTTPS and expected sanitized report response are verified. Require ALLOW_PRODUCTION_DNS and explicit host/user approval, not just a browser-provided boolean. DNS failure must not prevent private report downloads.

## Acceptance tests (implement under owned paths)

| Area | Positive | Negative |
|---|---|---|
| Contract | fixture and real responses match v1 | misspelled field/unknown source ID rejected |
| ZIP | two generated valid archives produce fixture counts | one ZIP, oversized/unsafe/encrypted archive, bad JSON/timestamp rejected |
| Window | earlier records excluded | no current timestamps => controlled error |
| Rename | consecutive/stable/unique linkage excluded | collision, instability, zero retained evidence, nonconsecutive pair unresolved |
| Audit | trusted evidence allows conservative absence | shell page/search absence/unknown does not confirm identity or inactivity |
| Counts | partition arithmetic preserved | model prose cannot change deterministic facts |
| Sources | real URL/platform/observed_at preserved | one observation cannot imply acceleration; missing remains null |
| AI | three distinct grounded bounded-time actions | invented URL/baseline/revenue/extra production time rejected |
| Nosana | real inference used in result | 401/402/no model/invalid JSON surfaced |
| Daytona | actual worker and report, matching hash | local-only or hello-world-only cannot pass integration gate |
| Privacy | no private handles in Nosana/public output | malicious text/HTML cannot execute or leak |
| Jobs | queue/poll/idempotency/concurrency work | wrong token, altered payload, restart behavior handled |
| DNS | record create and readback receipt | sandbox not public; conflict never overwritten |
| E2E | frontend -> API -> real providers -> report | failure/partial/mock badges truthful; buttons use live API |

Tests that use temporary fixtures must retain them in scoped ignored run folders; avoid automatic deletion-bearing teardown until approved. Existing upstream tests use TemporaryDirectory cleanup: port their assertions to retained fixtures instead of executing destructive teardown blindly.

A owns frontend transport/UI tests and final browser workflow verification. B owns backend behavior/security/provider tests and receipts. Architect checks ownership, frozen-contract hashes and real integrated behavior. A passing preparation validator is not an app or provider test.
