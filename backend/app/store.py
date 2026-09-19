"""In-memory, process-local run store. Jobs are LOST on process restart."""
from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def now() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


class RunState:
    def __init__(self, run_id: str, profile_fingerprint: str):
        self.run_id = run_id
        self.access_token = secrets.token_urlsafe(32)
        self.profile_fingerprint = profile_fingerprint
        self.status = "queued"
        self.stage = "validate"
        self.is_mock = False
        self.created_at = now()
        self.updated_at = self.created_at
        self.trace = []
        self.result = None
        self.error = None
        self.artifacts = {}          # name -> absolute Path (per-run allowlist)
        self.receipts = []
        self.sandbox_id = None
        self.public_token = None
        self.publication = None
        self.lock = threading.Lock()

    def touch(self):
        self.updated_at = now()

    def set_stage(self, stage):
        with self.lock:
            self.stage = stage
            if self.status == "queued":
                self.status = "running"
            self.touch()

    def add_trace(self, entry):
        with self.lock:
            self.trace.append(entry)
            self.touch()


class Store:
    def __init__(self):
        self._runs = {}
        self._idem = {}          # idempotency key -> (fingerprint, run_id)
        self._public = {}        # public token -> run_id
        self._lock = threading.Lock()

    def create(self, idem_key: str, fingerprint: str):
        """Returns (run, reused). Raises KeyError on a conflicting payload."""
        with self._lock:
            existing = self._idem.get(idem_key)
            if existing:
                prev_fp, run_id = existing
                if prev_fp != fingerprint:
                    raise KeyError("IDEMPOTENCY_CONFLICT")
                return self._runs[run_id], True
            run_id = "run_" + secrets.token_hex(8)
            run = RunState(run_id, fingerprint)
            self._runs[run_id] = run
            self._idem[idem_key] = (fingerprint, run_id)
            return run, False

    def get(self, run_id):
        return self._runs.get(run_id)

    def active_count(self):
        return sum(1 for r in self._runs.values() if r.status in ("queued", "running"))

    def register_public(self, token, run_id):
        with self._lock:
            self._public[token] = run_id

    def by_public(self, token):
        run_id = self._public.get(token)
        return self._runs.get(run_id) if run_id else None


STORE = Store()
