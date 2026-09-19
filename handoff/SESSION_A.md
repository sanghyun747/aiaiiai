# Session A — frontend implementer, production UX, repository publisher

Project: TrendPilot. Your role is EXECUTION, not redesign. Deliver a working frontend and create the project GitHub repository after local verification. The architect/supervisor owns product scope, frozen contracts and final merge. Session B independently owns API/providers.

## Workspace and ownership

Actual worktree: C:\Users\sangh\trendpilot-hackathon-20260919-ui
Branch: feat/frontend
Expected baseline: contracts-v2 / contract 1.1.0, identical to Session B. Verify branch, HEAD and status before editing. Stop on unexpected edits.

Read:
- AGENTS.md
- README.md
- contracts/HTTP.md
- contracts/v1.openapi.json
- fixtures/run-sample.json
- docs/PROVIDERS_AND_TESTS.md
- handoff/INTEGRATION.md

Normal file ownership is ONLY frontend/**. Never edit contracts, fixtures, backend, root source/config files or Session B's worktree. Put package.json/package-lock.json inside frontend. Local implementation commits contain only frontend/**.

Special exception explicitly requested by the user: Session A is the sole executor allowed to create the GitHub remote repository and perform the initial non-force push described below. This exception covers Git remote metadata and remote creation/push only; it does not grant permission to edit shared contract/root files or merge Session B.

Never delete files/data/test outputs or use destructive rollback without explicit user approval. Do not start a second DevSpace server. If a clone/test DevSpace is genuinely required, set DEVSPACE_GATE_KEY_FILE=C:\Users\sangh\trendpilot-hackathon-20260919-ui\.runtime\devspace-gate.key before launch and isolate all state/ports. Never inherit the production gate key.

## Product outcome

TrendPilot is a Personal SNS Growth Production Agent. It must not stop at "here are content ideas." For every returned experiment, the user should be able to leave the app knowing what to say, what to film, how to edit it, how the thumbnail should look, and how to package the post. Physical shooting remains the user's job.

The UI must clearly distinguish:
- SAFE BET: exploit an evidenced current strength.
- GROWTH EXPERIMENT: improve exactly one named weakness.
Neither label is a performance guarantee.

## Deliver in order

1. Build React + TypeScript + Vite under frontend. Required commands: npm run dev -- --host 127.0.0.1 --port 5317, npm run build, npm test. Keep dependencies tested and lockfile frontend-local. Disable destructive clean behavior; no rm/rimraf/automatic deletion.

2. Build one polished Korean product dashboard, not a marketing-only landing page. Required flow:
   입력 → 실제 처리 단계 → 계정/근거 요약 → 팔로워 변화 → SAFE BET/GROWTH EXPERIMENT → Production Package → 다운로드/게시.
   Make the primary product usable on a normal laptop and responsive on mobile.

3. Inputs: niche, audience, goal, format, weekly_minutes, query, demo/live, optional consecutive Instagram export pair, explicit cloud processing consent. Show "합성 예제" versus "실제 데이터" clearly. Never require Instagram login. Never pre-check cloud/public consent.

4. Use one typed API client generated/implemented against contract 1.1.0. Vite proxies /api and /p to 127.0.0.1:8317; use relative browser paths. multipart profile_json=JSON.stringify(Profile), optional old_export/current_export. Never manually set multipart Content-Type. Generate an unpredictable Idempotency-Key and preserve it only for retries of the same request. Run bearer token stays in memory/sessionStorage, never URL/log.

5. Support explicit VITE_USE_MOCK=true using fixtures/run-sample.json and a persistent MOCK banner. Never silently fall back to mock. Synthetic input through real Nosana/Daytona is not mock; render source_mode and trace.mode separately.

6. Poll queued/running every 1500ms and stop only on terminal status. Status/stage is API truth, not a timer. Handle partial, failed, invalid ZIP pair, missing consent/provider/credit, token failure, network failure and duplicate click. null renders "미확인", never 0.

7. Render evidence and follower analysis conservatively:
   - show source/platform/observed_at/limitations;
   - a single observation is not acceleration;
   - YouTube evidence is not Instagram trend proof;
   - raw_missing is separate from relationship_absent, renamed, outside_window, unresolved;
   - export count difference is not proven net follower growth;
   - never say a post caused an unfollow.

8. Render exactly three action cards when succeeded. Visually identify strategy_mode. At least one SAFE BET and one GROWTH EXPERIMENT must be present. A growth experiment must show weakness_target. Each card must show title, evidence links, fit reason, hook A/B, time budget, CTA, metric and success rule.

9. Build a complete Production Package viewer for every action with five first-class tabs/sections:
   - SCRIPT: hook, intro, body, ending, CTA.
   - SHOT LIST: ordered scene number, duration, visual, narration, subtitle.
   - EDITING GUIDE: pace, caption style, cut plan, music direction, B-roll notes.
   - THUMBNAIL PLAN: concept, exact thumbnail text, composition, generation prompt.
   - PUBLISHING PACKAGE: title, description, hashtags, CTA, target metric, posting notes.
   Provide copy-to-clipboard where useful. Do not claim the app filmed footage or rendered a finished video unless the API provides a verified media artifact.

10. Artifact downloads: support report.md and every path returned in result.artifacts using authenticated blob fetch. Do not construct host paths or accept arbitrary artifact names. Surface content-strategy.json, script.md, shot-list.json, editing-guide.md, thumbnail-plan.md and publishing-package.md if B actually returns them. Mock fixture may have fewer artifacts; do not fabricate missing files.

11. DNSimple publish is a distinct explicit consent action. Sandbox status must read "DNSimple 테스트 레코드 생성 · 공개 접속 불가". Never fabricate a working URL. Production publish controls stay disabled unless the backend says they are truly configured/approved.

12. Tests: typed fixture/schema assumptions, multipart serialization, state transitions, strategy_mode labels, growth weakness display, all five production package views, artifact download auth, null display, source/mode labeling and failure paths. When B is available, run one real frontend→API→Nosana/Daytona→artifact-download synthetic vertical slice using the approved host browser. Do not write Playwright/Selenium/CDP automation on this host.

## GitHub repository creation — Session A only

Do this only after frontend build/tests pass and before final handoff.

1. Run git remote -v. If origin already exists, DO NOT replace, rename or delete it. Record the existing remote and skip creation.
2. Run gh auth status. If GitHub CLI is unavailable/not authenticated, report the blocker; do not search secret stores or invent credentials.
3. If no origin exists and gh is authenticated, create ONE new repository under the authenticated user's account. Preferred name: trendpilot. If that exact name is unavailable, use trendpilot-hackathon-20260919. Create it PRIVATE by default. Do not change visibility to public without a later explicit instruction.
4. Add it as origin through the normal gh/git flow. Do not create a second remote with a competing name.
5. Push the shared main baseline first so main is the repository default history, then push feat/frontend with upstream tracking. No force push, history rewriting, branch deletion or tag deletion. Do NOT push/merge feat/backend on B's behalf.
6. Record repository owner/name and remote URL in frontend/HANDOFF.md. Do not expose credentials.
7. This user request authorizes the one-time repo creation and initial pushes above. Any later public visibility change, destructive repo setting, branch deletion or overwrite remains out of scope.

## Acceptance and handoff

Build/tests must pass from this exact worktree. Run python -X utf8 -B docs/verify_prep.py. After a frontend-only commit run it with --base contracts-v2 --owner A.

Write frontend/HANDOFF.md with:
- frontend commit hash and changed files;
- exact build/test commands and results;
- app port/session IDs;
- mock vs live checks;
- production package UX verified;
- artifact download verification;
- GitHub repository creation/push result;
- exact blockers;
- retained processes if any.

Stop test servers you own unless the user explicitly wants the demo kept open. Do not call mock-only behavior integrated. Do not merge B or modify the contract to fit shortcuts.
