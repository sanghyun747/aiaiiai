# Architect-only integration runbook

This is not an execution handoff to A/B. The architect freezes contracts and reviews both implementations. No claim of conflict-free merging without checks; disjoint ownership prevents ordinary textual conflicts but semantic integration still needs real tests.

## Prepared layout

- Main/design repo: C:\Users\sangh\trendpilot-hackathon-20260919 ; branch main
- A worktree: C:\Users\sangh\trendpilot-hackathon-20260919-ui ; feat/frontend
- B worktree: C:\Users\sangh\trendpilot-hackathon-20260919-api ; feat/backend
- Both start at tag contracts-v2. All preparation files are present in both worktrees.
- Dedicated integration worktree will be created only after both branches are ready, under a previously nonexistent path. No worktree/branch deletion or destructive reset.

## Entry gates before parallel implementation

1. Confirm the organizer permits existing code/templates and preparatory material. The event page confirms sponsor integration, team size and demo format, but not every reuse restriction. Retain upstream attribution and distinguish pre-existing code from hackathon implementation.
2. Ensure sponsor accounts/credits and a DNSimple sandbox token/zone can be supplied locally. Current environment-key absence is not an account/credit check. No secrets in chat.
3. Verify both branches point to the SAME contracts-v2 baseline and both worktrees are clean.
4. Assign A frontend/** and B backend/** only. No shared root lockfile/environment/config. Frontend 5317; backend 8317; localhost only.
5. This preparation session does not start implementer agents, apps or new DevSpace servers. The user opens two execution sessions with the respective handoff.

## Interface freeze

contracts/v1.openapi.json, contracts/HTTP.md and fixtures/** are architect-owned. Branches must preserve them byte-for-byte. Python verifier checks the used JSON Schema subset, internal references, fixture invariants/hash and branch path ownership; it is NOT a full OpenAPI conformance validator and does not test remote providers.

Each executor runs, from their own project directory:

    python -X utf8 -B docs/verify_prep.py
    python -X utf8 -B docs/verify_prep.py --base contracts-v2 --owner A

B uses --owner B. The ownership check covers committed, staged, unstaged and nonignored untracked paths. No deletion is authorized even in the owned folder. Executor HANDOFF files must name exact commits and tested results. Requests to change v1 go to the architect; either defer them or issue one coordinated revision before both continue.

## Integration commands (architect only, after checking paths and branch state)

Use actual verified branch tips, not stale hashes from a previous session. Example Git Bash commands:

    git -C C:/Users/sangh/trendpilot-hackathon-20260919 worktree list --porcelain
    git -C C:/Users/sangh/trendpilot-hackathon-20260919-ui status --short
    git -C C:/Users/sangh/trendpilot-hackathon-20260919-api status --short
    git -C C:/Users/sangh/trendpilot-hackathon-20260919 diff --name-status contracts-v2..feat/frontend
    git -C C:/Users/sangh/trendpilot-hackathon-20260919 diff --name-status contracts-v2..feat/backend

If either branch modifies forbidden files, asks to delete, or has uncommitted changes, stop and correct with a new safe commit. Do not drop changes or reset branches.

After both checks pass, choose a new unused integration path and branch, then:

    git -C C:/Users/sangh/trendpilot-hackathon-20260919 worktree add -b integration/mvp C:/Users/sangh/trendpilot-hackathon-20260919-integration contracts-v2
    git -C C:/Users/sangh/trendpilot-hackathon-20260919-integration merge --no-ff feat/backend -m "Integrate scoped backend"
    git -C C:/Users/sangh/trendpilot-hackathon-20260919-integration merge --no-ff feat/frontend -m "Integrate scoped frontend"

Never use 'ours/theirs' to conceal a conflict. If a conflict occurs, retain the state, inspect ownership and fix specific content with review. Session A has explicit user authorization for the one-time GitHub repository creation and initial non-force pushes described in SESSION_A.md. Architect integration/final push still requires review; no force push, branch deletion or destructive remote change. No deletion of old worktrees afterwards.

## Actual completion gate

Build/install each directory independently using its tested lockfile/requirements. Run A's frontend tests and B's backend tests. Run the prep verifier. Start backend/frontend in managed exec sessions only. Keep 127.0.0.1 bindings and use the approved host browser.

Required integration demonstration: input -> HTTP 202 -> real stages -> Nosana-generated grounded SAFE BET/GROWTH EXPERIMENT actions -> complete Production Package for each action -> Daytona-computed synthetic follower case and generated production artifacts -> browser downloads at least one Daytona-generated artifact with matching SHA-256. Then explicit DNSimple sandbox publication -> create/readback receipt with public_url=null. A demo with synthetic DATA and real EXECUTION is validly labeled; mock/replayed execution is not a real integration receipt.

Negative demo: missing current ZIP or an unavailable provider shows an explanatory validation/partial/error state and never fabricated success. Check null values, unknown audits, source links, all experiment source references, time-budget constraint, and provider traces. Inspect the actual network/result, not only screenshots.

Public deployment is outside the default localhost demo. Do not expose the unauthenticated create-run endpoint to the internet; before public operation add an approved operator access gate, rate limits and provider-credit controls. Private uploads remain off until privacy and access tests pass. Public report publishing requires separate consent and sanitized content. Domain production work requires explicit approval and real DNS/TLS/hosting checks.

Final report separates: code/build pass, unit tests, mock UI tests, Production Package UX, GitHub repo creation/push, real source acquisition, real Nosana, real Daytona worker/production artifacts, DNSimple sandbox and public URL. List each as PASS/FAIL/NOT RUN with evidence. Report remaining processes/resources and retention; stop owned test processes/sandboxes where permitted, never delete data silently.
