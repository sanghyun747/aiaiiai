"""Daytona sandbox adapter.

Deterministic Python - not the LLM - computes follower counts, partitions,
hashes and the final serialization, inside a real sandbox. Arbitrary internet
is blocked from inside the sandbox, so no provider call is made from there.
Only minimized synthetic follower records are uploaded.
"""
from __future__ import annotations

import os
import time

from .errors import ProviderError


class DaytonaRun:
    def __init__(self):
        self.sandbox = None
        self.sandbox_id = None
        self._client = None

    def start(self):
        if not os.environ.get("DAYTONA_API_KEY"):
            raise ProviderError("PROVIDER_UNAVAILABLE", "DAYTONA_API_KEY is not configured.", False)
        try:
            from daytona import Daytona

            self._client = Daytona()
            self.sandbox = self._client.create()
        except Exception as exc:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"Daytona sandbox create failed: {type(exc).__name__}: {exc}", True)
        self.sandbox_id = getattr(self.sandbox, "id", None)
        return self.sandbox_id

    def upload(self, local_path: str, remote_path: str):
        try:
            self.sandbox.fs.upload_file(local_path, remote_path)
        except Exception as exc:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"Daytona upload failed: {type(exc).__name__}: {exc}", True)

    def exec(self, command: str, timeout: int = 120):
        try:
            res = self.sandbox.process.exec(f"bash -lc '{command}'", cwd=None, timeout=timeout)
        except Exception as exc:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"Daytona exec failed: {type(exc).__name__}: {exc}", True)
        return res.exit_code, (res.result or "")

    def download(self, remote_path: str) -> bytes:
        try:
            return self.sandbox.fs.download_file(remote_path)
        except Exception as exc:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"Daytona download failed: {type(exc).__name__}: {exc}", True)

    def stop(self):
        """Delete the sandbox we created. Only sandboxes owned by this run."""
        if self.sandbox is None:
            return None
        try:
            self.sandbox.delete()
            return "deleted"
        except Exception as exc:  # pragma: no cover
            return f"left running: {type(exc).__name__}"
