# backend/vendor provenance

## follower_diff/analyzer.py

- **Status: CLEAN-ROOM REIMPLEMENTATION — not a copy of the original skill.**
- The original skill `instagram-follower-diff` lives on the teammate's Windows box at
  `C:\Users\sangh\SKILL\instagram-follower-diff` and is NOT present on this Linux/WSL machine.
  Its `scripts/instagram_follower_diff.py`, `SKILL.md` and `methodology.md` were never read here,
  so no original path SHA-256 can be recorded.
- Written on 2026-09-19 directly from the frozen requirements in `contracts/HTTP.md`
  ("Follower invariants") and the synthetic expectations in `fixtures/follower-case.json`.
  It reproduces the required invariants and the conservative rename rule; it does not reproduce
  the original script's code, Markdown output or internal naming.
- **Pending replacement**: when a copy of the original script is available, place it here, record
  its original path, copy date and SHA-256 in this file, adapt the COPY only, and re-run
  `backend/tests/test_followers.py`. The original skill and any real user ZIPs must never be
  edited, moved or overwritten, and no private report, memory file or real export enters Git.
- Behaviour notes: stdlib only, deterministic, offline. It is uploaded unchanged into the Daytona
  sandbox and executed there. It never infers a cause for an unfollow, never resolves a rename
  from current-activity evidence alone, and the fixture's synthetic audit is applied only when
  `input_kind == "synthetic"`.
