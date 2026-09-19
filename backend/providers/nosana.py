"""Nosana hosted inference adapter (OpenAI-compatible).

https://inference.nosana.com/v1 with Authorization: Bearer $NOSANA_API_KEY.
Nosana receives anonymised aggregates and allowed source ids only: never
usernames, account ids, ZIPs or raw relationship records. The model can never
alter follower counts, sources or observations - those are computed
deterministically and merged back in code.
"""
from __future__ import annotations

import json
import os
import re
import time

from .errors import ProviderError

BASE_URL = os.environ.get("NOSANA_BASE_URL", "https://inference.nosana.com/v1")
_PREFERRED = re.compile(r"(instruct|chat|qwen|llama|mistral|gemma|deepseek)", re.I)


def _client():
    key = os.environ.get("NOSANA_API_KEY")
    if not key:
        raise ProviderError("PROVIDER_UNAVAILABLE", "NOSANA_API_KEY is not configured.", False)
    from openai import OpenAI

    return OpenAI(api_key=key, base_url=os.environ.get("NOSANA_BASE_URL", BASE_URL), timeout=120.0)


def pick_model(client=None) -> str:
    client = client or _client()
    try:
        models = client.models.list().data
    except Exception as exc:  # pragma: no cover - network
        raise ProviderError("PROVIDER_UNAVAILABLE", f"Nosana model listing failed: {type(exc).__name__}: {exc}", True)
    available = []
    for m in models:
        raw = getattr(m, "model_extra", None) or {}
        if raw.get("available") is False:
            continue
        available.append(m.id)
    if not available:
        raise ProviderError("MODEL_UNAVAILABLE", "No available Nosana model in /v1/models.", True)
    for mid in available:
        if _PREFERRED.search(mid):
            return mid
    return available[0]


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON object in model output")
    depth, in_str, esc, opener = 0, False, False, text[start]
    closer = "}" if opener == "{" else "]"
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unterminated JSON in model output")


def complete_json(system: str, user: str, model: str = None, client=None, max_tokens: int = 6000):
    """Returns (parsed_json, receipt). Raises ProviderError on real failure."""
    client = client or _client()
    model = model or pick_model(client)
    started = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # pragma: no cover - network
        raise ProviderError("PROVIDER_UNAVAILABLE", f"Nosana inference failed: {type(exc).__name__}: {exc}", True)
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    receipt = {
        "model": getattr(resp, "model", model),
        "remote_id": getattr(resp, "id", None),
        "duration_ms": int((time.time() - started) * 1000),
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        } if usage else None,
    }
    return _extract_json(text), receipt, text
