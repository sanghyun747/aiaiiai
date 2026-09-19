# Session A — frontend implementer and integration UX tester

Project: TrendPilot. Your role is EXECUTION, not redesign. Deliver a working frontend, not only a plan. The architect/supervisor owns product scope, contracts and merging. A separate Session B owns the API and providers.

## Workspace and ownership

Actual worktree: C:\Users\sangh\trendpilot-hackathon-20260919-ui
Branch: feat/frontend
Expected baseline: the same contracts-v1 tag/commit as Session B. Verify git -C <worktree> branch --show-current and status before editing. Stop on unexpected existing edits. Follow host setup at C:\Users\sangh, reuse the existing approved DevSpace connection, and scope every command to the assigned worktree. Do not operate on the home Git repo.

Read AGENTS.md, README.md, contracts/HTTP.md, contracts/v1.openapi.json, fixtures/run-sample.json and docs/PROVIDERS_AND_TESTS.md. Write ONLY frontend/**. Never edit contracts, fixtures, backend, root configuration or the other worktree. Place dependencies and package-lock.json inside frontend, not at the root. Local commits may contain only frontend/**; no remote push or merging.

Never delete files/data/test outputs or use destructive rollback without user approval. Do not start a new DevSpace server. If a test/clone DevSpace server genuinely becomes necessary, its DEVSPACE_GATE_KEY_FILE must point to C:\Users\sangh\trendpilot-hackathon-20260919-ui\.runtime\devspace-gate.key before launch, with isolated ports/state; never inherit the production key. App runtime and Daytona do not require starting another DevSpace.

## Deliver in order

1. Build React + TypeScript + Vite at frontend. Scripts: npm run dev -- --host 127.0.0.1 --port 5317, npm run build, npm test. Select tested dependencies, commit a frontend-only lockfile. No root workspace migration or framework redesign. Disable Vite build.emptyOutDir and avoid clean/rimraf tasks; prefer new scoped build output when preserving earlier artifacts is needed. No deletion without approval.
2. Create a professional Korean dashboard with one flow: inputs -> real stage/status -> result. Three result areas: 관측 근거 / 팔로워 변화 / 다음 실험. Use readable hierarchy, generous spacing, responsive layout and useful empty/error states. No unrelated landing page, accounts, payments, video editor or admin screen.
3. Input topic/audience, goal, format, weekly time and query. Explicitly distinguish '합성 예제로 실행' from '실제 데이터로 실행'. Offer optional ZIP pair, not a mandatory Instagram login. Real-cloud processing consent is unchecked by default, explained before enabling upload. Public deployment stays synthetic-only until approved.
4. Use one typed API client and the exact frozen wire contract. Vite proxies /api and /p to 127.0.0.1:8317; use relative browser paths. multipart profile_json is JSON.stringify(Profile), optional old_export/current_export; do not manually set multipart Content-Type. Generate unpredictable Idempotency-Key; preserve it for retries of the SAME request. Store per-run bearer token only in memory/sessionStorage, not public URLs or logs.
5. Initially render the frozen fixture through an EXPLICIT mock flag (frontend VITE_USE_MOCK=true) with a persistent MOCK banner. Do not silently fall back from API error to mock. Synthetic inputs through actual providers are not mock execution: display source_mode and trace.mode separately. Live is the default integrated mode.
6. Poll queued/running every 1500ms; stop at terminal. Stages come from the API, not fake timer success. Handle partial result, invalid ZIP pair, consent missing, provider missing/credit error, wrong token, network error and duplicate clicks. Render null as 미확인, not 0. Health.configured is key presence, not integration success.
7. Result must show observations with source links/platform/observed_at, limitations and three complete experiments. Explain a single observation is not rising acceleration. Do not label YouTube evidence as Instagram trend proof. Followers: raw_missing separately from relationship_absent, renamed, outside_window and unresolved. Export-count difference is not proven net growth. Timestamp continuity is a matching rule, not absolute account-ID proof. Never say 'this post caused these unfollows'.
8. Report download fetches the authenticated Markdown endpoint as a blob, then saves. Do not expose bearer token in a link. Use fixture/report-sample.md only in explicit mock mode. Publish is a distinct consent action: POST publish, display sandbox_record_created as 'DNSimple 테스트 레코드 생성 · 공개 접속 불가', never a fake working URL. Production controls disabled unless actually approved/configured.
9. Add frontend tests for typed fixture, API serialization, state transitions, null display, unknown-source/mode labeling and error paths. When B becomes available, use actual API on 8317 and the approved host browser for one complete end-to-end flow. Do not write Playwright/Selenium/CDP scripts on this host or use authenticated Instagram.

## Acceptance and handoff

Build and tests must pass from the exact worktree. Verify contract fixture with python -X utf8 -B docs/verify_prep.py. After committing only frontend paths, run that verifier with --base contracts-v1 --owner A. Do not call mock-only work integrated.

Write frontend/HANDOFF.md with commit hash, tested commands and results, app port/session IDs, mock vs live checks, exact blockers, and file list. Secrets and real follower identifiers must not appear. Stop test servers you own when finished unless the user explicitly wants the demo kept open; report any retained server/session. Remain within frontend ownership even after you finish early: improve integration tests instead of editing backend. Propose contract changes to the architect; do not implement a breaking wire change yourself.
