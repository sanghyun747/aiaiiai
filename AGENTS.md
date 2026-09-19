# TrendPilot execution contract

This is a preparation repository, not a completed application. Read README.md, contracts/HTTP.md, contracts/v1.openapi.json and your assigned handoff before implementation. User-facing text is Korean; agent handoffs are concise English.

## Non-negotiable safety

- Never delete files, data, backups, branches or worktrees without explicit user confirmation. This includes temporary test outputs. Do not run git clean, reset --hard, worktree remove, automatic cleanup scripts or deletion-bearing test teardown without approval. Preserve new test outputs in a scoped ignored run directory.
- Do not edit, rename, move, extract, overwrite or delete the source skill or original Instagram ZIPs. Only a copy inside backend/vendor may be adapted. Record provenance. No private exports, original reports or real handles in Git.
- Do not upload host files to external file-sharing services. Real Instagram data must not be sent to Daytona or any provider without the user's explicit data-processing approval. Default demos use synthetic data only.
- Nosana sees anonymized aggregate follower statistics, not usernames, account IDs, ZIPs or private relationship records. Public reports omit follower identifiers and private per-account data.
- No authenticated Instagram fallback, profile-store access, cookie extraction, CAPTCHA bypass, mass scraping, social writes, automated follows, likes or messages. Public/manual audit may be imported through trusted server-side evidence only.
- Ask before production DNS mutation, purchase, payment, public deployment or sending private material. A sandbox API call is not proof of public publication. Exception: the user explicitly authorized Session A to create the initial private GitHub repository and perform the non-force initial pushes defined in handoff/SESSION_A.md. That exception does not authorize public visibility changes, force push, deletion, or later destructive remote actions.
- Do not change Tailscale funnel/serve, existing DevSpace configuration or other projects. Bind local development servers to 127.0.0.1 only. Never start another DevSpace server just to run the app.
- If a clone/test DevSpace server is actually required, set DEVSPACE_GATE_KEY_FILE to a unique path within that worktree's .runtime/ directory BEFORE launch. Never inherit/reuse the production gate key. Also isolate other instance state/ports. Do not print key contents. This is separate from Daytona.
- Respect approval, pause, lease and browser read-only controls. Never retry around an explicit access denial.
- Back up existing files before broad edits. Do not edit the home repository. Use git -C with the exact assigned worktree.

## Ownership and concurrency

- Session A writes only frontend/**, including frontend/package.json, frontend/package-lock.json, frontend/tests/** and frontend/HANDOFF.md. Its only non-file ownership exception is the one-time GitHub remote creation/initial push defined in SESSION_A.md.
- Session B writes only backend/**, including backend/requirements.txt, backend/tests/**, backend/vendor/** and backend/HANDOFF.md.
- Architect owns root files, contracts/**, fixtures/**, docs/** and handoff/**. Both executors read these paths but NEVER edit them.
- Never create a root package.json/lockfile/.env shared by both sessions. Configuration samples and dependency locks live under the owning directory. Runtime secrets live in ignored scoped files and are never committed.
- Work on separate branches/worktrees from the same frozen contract commit. No branch switching, merging or rebasing by executors. Stage only owned paths, never git add . or git add -A from a shared root. Stop/report an unexpected staged path.
- No contract change by negotiation between executors. Propose it to the architect. Implement behind frozen contract 1.1.0 / contracts-v2 until both sides receive an approved revision.
- Stop/report pre-existing uncommitted changes; do not overwrite them. Other agents may be working concurrently.

## Completion truth

- UI mock, synthetic inputs, cached evidence and live provider execution are distinct. Label each separately.
- Passing contract/fixture checks does not mean providers or the app work. Every claimed provider integration needs a real request receipt and visible user-facing output.
- Raw follower diff categories remain preliminary until the audit gate. LLM prose cannot change deterministic counts or audit statuses. ProductionPackage text is generated guidance, not proof that filming or finished-video rendering occurred.
- Unknown evidence, missing metrics, blocked profiles and absent source results remain unknown. Never infer causality between a post and individual unfollows.
- Freeze feature scope before integration. Leave service/session IDs and reasons in the final report if any processes remain running. Do not leave unreported test servers or long-running agents.
