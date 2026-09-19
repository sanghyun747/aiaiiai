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
_EXCLUDE = re.compile(r"(embed|rerank|whisper|tts|vision-only)", re.I)


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
        if _EXCLUDE.search(m.id):
            continue  # embedding/rerank models cannot serve chat completions
        available.append(m.id)
    if not available:
        raise ProviderError("MODEL_UNAVAILABLE", "No available Nosana model in /v1/models.", True)
    for mid in available:
        if _PREFERRED.search(mid):
            return mid
    return available[0]


def _extract_json(text: str):
    """Tolerant extraction: strips reasoning blocks and code fences, then scans
    every candidate start for the first balanced JSON value that parses."""
    text = re.sub(r"<think>.*?</think>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<\|?(?:channel|analysis|reasoning)[^>]*>.*?<[^>]*>", " ", text, flags=re.S | re.I)
    text = text.strip()
    if "```" in text:
        fenced = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, flags=re.S)
        if fenced:
            text = max(fenced, key=len)
    for start in range(len(text)):
        opener = text[start]
        if opener not in "{[":
            continue
        closer = "}" if opener == "{" else "]"
        depth, in_str, esc = 0, False, False
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
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("no parseable JSON object in model output (%d chars)" % len(text))


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
    choice = resp.choices[0]
    text = choice.message.content or ""
    if choice.finish_reason == "length":
        raise ProviderError(
            "AI_OUTPUT_INVALID",
            f"Nosana output was truncated at max_tokens={max_tokens} (finish_reason=length); "
            "no valid JSON was produced.", True)
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
