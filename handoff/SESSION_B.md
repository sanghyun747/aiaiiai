# Session B — API, analytics, Production Agent and sponsor-provider implementer

Project: TrendPilot. Execute the frozen MVP; do not redesign it. Architect owns scope/contracts/final merge. Session A independently builds frontend and owns GitHub remote creation. You own backend/** only.

## Workspace and ownership

Actual worktree: C:\Users\sangh\trendpilot-hackathon-20260919-api
Branch: feat/backend
Expected baseline: contracts-v2 / contract 1.1.0, identical to Session A. Verify branch, HEAD and status first. Stop on unexpected edits.

Read:
- AGENTS.md
- README.md
- contracts/HTTP.md
- contracts/v1.openapi.json
- fixtures/follower-case.json
- fixtures/run-sample.json
- docs/PROVIDERS_AND_TESTS.md
- handoff/INTEGRATION.md

Write ONLY backend/**: API, vendor copy, tests, provider adapters, runtime templates, generated-artifact code, README and HANDOFF. No root/frontend/contract/fixture edits. Commit backend paths only. Never merge/rebase/push. Session A owns initial GitHub remote creation; you must not race it.

No deletion of files/data/test outputs, destructive rollback or automatic cleanup without explicit user approval. Never overwrite original skill/user ZIPs. Do not start a second DevSpace server. If a test DevSpace is genuinely needed, set DEVSPACE_GATE_KEY_FILE=C:\Users\sangh\trendpilot-hackathon-20260919-api\.runtime\devspace-gate.key and isolate ports/state.

## Product outcome

Backend must turn grounded evidence into a complete shooting-excluded production handoff, not just idea text.

Every successful run returns exactly three actions:
- at least one strategy_mode=safe_bet;
- at least one strategy_mode=growth_experiment;
- each growth experiment targets exactly one weakness_target.

Every action must include:
- script;
- ordered shot_list;
- editing_plan;
- thumbnail_plan;
- publishing_package.

The system may say it generated an editing GUIDE. It must not claim a finished video was edited/rendered unless real user-recorded media passed through an actual renderer and a verified media artifact exists. No such claim is required for P0.

## Execute in this order

1. PRE-FLIGHT FIRST. Create backend/.env.example with empty placeholders only. Check official/current Nosana, Daytona, DNSimple and YouTube setup; check only normally supplied environment/config locations. Verify key presence, Nosana model/credit availability, a synthetic Daytona smoke job, and DNSimple sandbox read if an explicit sandbox token/account/zone is supplied. Record actual success/blocker. Key presence is not integration success. No production DNS, purchases or private user data upload without the required consent/approval.

2. Implement FastAPI/Pydantic on 127.0.0.1:8317 for every frozen 1.1.0 route: health/createRun/getRun/report artifact/generic artifact/publish/public report. Bounded in-memory worker pool (<=2 jobs), truthful stages, random per-run tokens, idempotency key/payload binding, upload limits and structured errors. Jobs are process-local/no persistence. Pin tested dependencies in backend/requirements.txt.

3. Copy C:\Users\sangh\SKILL\instagram-follower-diff\scripts\instagram_follower_diff.py into backend/vendor using approved file tools. Read original SKILL.md and methodology.md. Record original path/date/SHA-256 in backend/vendor/PROVENANCE.md. Adapt the COPY only. Do not import private reports/memory/real ZIPs into Git.

4. Generate synthetic ZIP test inputs from fixtures/follower-case.json under a NEW ignored backend/.runtime/<run-id> directory and retain them. Validate schema, file pair, size and archive safety. For approved real cloud uploads, minimize follower records before Daytona; never send unrelated export content.

5. Implement follower audit after raw diff exactly as the frozen contract states. Every comparable candidate gets audit status/evidence/time/access context. Stable timestamp rename matching requires consecutive exports, retained valid timestamp stability and full-export uniqueness. Ambiguous, blocked or nonconsecutive remains unresolved. Current activity evidence alone does not resolve rename. No authenticated Instagram fallback, unauthenticated scraping or arbitrary client-supplied "verified" status.

6. Acquire bounded public reference evidence using YouTube official API when configured. Preserve URL/platform/observed_at and only deterministic descriptive metrics. If unavailable use explicit demo/cached mode with truthful labels. Never invent live evidence, acceleration or video-content analysis from metadata.

7. Nosana pass 1: produce a constrained analysis/strategy plan from anonymized profile/aggregates/source IDs. Nosana receives no follower usernames/fbid/raw ZIPs.

8. Nosana pass 2: produce exactly three schema-valid actions grounded in existing source IDs. Requirements:
   - at least one SAFE BET exploiting an evidenced fit;
   - at least one GROWTH EXPERIMENT targeting one named weakness;
   - distinct hypotheses, not paraphrases;
   - total production_minutes <= weekly_minutes;
   - no invented baseline, follower number, probability, revenue or trend ranking;
   - complete ProductionPackage for EACH action:
     ScriptPackage: hook/intro/body/ending/cta.
     ShotList: order/duration_sec/visual/narration/subtitle.
     EditingPlan: pace/caption_style/cut_plan/music_direction/b_roll_notes.
     ThumbnailPlan: concept/text/composition/generation_prompt.
     PublishingPackage: title/description/hashtags/cta/target_metric/posting_notes.
   Validate output in code. At most one AI JSON repair. Never silently fall back to another model/provider and label it Nosana/live.

9. Daytona: execute fixed safe Python code in a real sandbox for the synthetic/live-provider vertical slice. Deterministic code—not the LLM—computes follower counts, partitions, hashes and final validated serialization. Materialize validated strategy into these actual files where applicable:
   - report.md
   - content-strategy.json
   - script.md
   - shot-list.json
   - editing-guide.md
   - thumbnail-plan.md
   - publishing-package.md
   The text files may contain all three actions with clear headings. Download each generated file, verify SHA-256 locally and populate result.artifacts ONLY for files actually produced. Generic artifact endpoint must use a per-run allowlist, not an arbitrary filesystem path.

10. Report generation must include evidence citations, limitations, SAFE BET/GROWTH EXPERIMENT labels and all five Production Package sections. Public/sanitized output contains no follower usernames, private audit rows, bearer tokens or provider secrets. Do not render untrusted model HTML.

11. DNSimple publish stays separate from run success. Minimum sponsor proof: explicit sandbox record creation + readback after user action when configured. Return public_url=null and sandbox_record_created for sandbox. Production remains disabled unless approval, actual DNS resolution, TLS and report route are all verified. Never overwrite/delete conflicting existing records.

12. Tests must cover: contract 1.1.0, exactly three actions, safe+growth presence, growth weakness required, production package completeness, shot order, weekly time budget, invented source rejection, follower-diff/audit negatives, malicious ZIP/input, provider failures, job token/idempotency, generic artifact allowlist, artifact SHA-256 and sanitized publication. Support A's real API integration rather than changing the frozen contract.

13. Priority rule: first complete one full synthetic-input + LIVE Nosana + LIVE Daytona vertical slice with actual production files. Then DNSimple sandbox. Advanced charts, OAuth, payment, databases, multi-platform scraping and automatic posting are out of P0. Do not spend P0 time building a video editor. If actual automatic editing is later added, it requires user-recorded footage, separate media/security constraints and verified media output; never fake it from an editing guide.

## Required final evidence

Run python -X utf8 -B docs/verify_prep.py. After backend-only commit run it with --base contracts-v2 --owner B.

Write backend/HANDOFF.md with:
- commit and file list;
- exact launch/test commands and outputs;
- provider/model names and receipt/remote IDs where available;
- mock/live/synthetic distinction;
- Daytona sandbox ID and output hashes;
- generated production artifact names/hashes;
- DNSimple state;
- missing keys/credits/config;
- security/retention limits and retained runtime files/processes.

Stop owned test processes and stop (do not delete) owned Daytona sandboxes where permitted; report what remains. No screenshots/secrets/real follower lists in public evidence.

Do not report "MVP complete" until Session A's frontend successfully creates a real run, receives the provider-backed result and downloads a Daytona-generated production artifact. If a provider is blocked, deliver working adapters/tests and explicit blockers without pretending sponsor integration passed.
