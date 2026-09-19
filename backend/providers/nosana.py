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
from pathlib import Path

from .errors import ProviderError

BASE_URL = os.environ.get("NOSANA_BASE_URL", "https://inference.nosana.com/v1")
_PREFERRED = re.compile(r"(instruct|chat|qwen|llama|mistral|gemma|deepseek)", re.I)
_EXCLUDE = re.compile(r"(embed|rerank|whisper|tts|vision-only)", re.I)
_REJECTS_JSON_MODE = re.compile(
    r"(response_format|json_object|unsupported|unrecognized|unknown.{0,20}(param|field)|400|422)", re.I)
# The qwen3 reasoning model needs headroom: with a small budget it returns
# content=null and spends the whole budget on the reasoning field.
MIN_MAX_TOKENS = 4000
RAW_DUMP = Path(__file__).resolve().parent.parent / ".runtime" / "nosana_last_raw.txt"


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


def _strip_wrappers(text: str, drop_open_think: bool = False) -> str:
    """Remove reasoning blocks and code fences that precede the JSON payload."""
    # qwen3 emits <think>...</think> before the answer; a truncated open tag is
    # also possible, so drop an unterminated trailing <think> too.
    text = re.sub(r"<think>.*?</think>", " ", text, flags=re.S | re.I)
    if drop_open_think:
        # An unterminated <think> means the answer never started; only used as a
        # last resort, because it would otherwise swallow a valid payload.
        text = re.sub(r"<think>.*$", " ", text, flags=re.S | re.I)
    text = re.sub(r"<\|?(?:channel|analysis|reasoning)[^>]*>.*?<[^>]*>", " ", text, flags=re.S | re.I)
    text = text.strip()
    if "```" in text:
        fenced = re.findall(r"```[a-zA-Z]*\s*\n(.*?)```", text, flags=re.S)
        if fenced:
            text = max(fenced, key=len).strip()
        else:  # unterminated fence: keep everything after the opener
            text = re.sub(r"^```[a-zA-Z]*\s*\n", "", text).replace("```", " ").strip()
    return text


def _first_balanced(text: str):
    """First balanced {...} / [...] value, by brace counting, string-aware.
    Scans left to right so an object nested inside an array is not preferred."""
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
    return _MISSING


_MISSING = object()


def _extract_json(text: str):
    """Tolerant extraction: strip reasoning blocks and code fences, then take
    the first balanced JSON value that parses. Objects are preferred."""
    length = 0
    for drop_open_think in (False, True):
        cleaned = _strip_wrappers(text, drop_open_think)
        length = max(length, len(cleaned))
        if not cleaned:
            continue
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        found = _first_balanced(cleaned)
        if found is not _MISSING:
            return found
    raise ValueError("no parseable JSON object in model output (%d chars)" % length)


def _dump_raw(text: str, note: str = "") -> str:
    """Persist the raw model text so a parse failure is diagnosable. Contains
    only model output built from anonymised aggregates - no secrets."""
    try:
        RAW_DUMP.parent.mkdir(parents=True, exist_ok=True)
        RAW_DUMP.write_text(
            f"# nosana raw output dump {time.strftime('%Y-%m-%dT%H:%M:%S')} {note}\n"
            f"# length={len(text)}\n\n{text[:2000]}",
            encoding="utf-8")
    except OSError:
        pass
    return text[:2000]


def _message_text(choice) -> str:
    """Read message.content; some endpoints return content=null plus a separate
    reasoning field when max_tokens is small. Fall back to that, never invent."""
    msg = choice.message
    text = getattr(msg, "content", None) or ""
    if text.strip():
        return text
    extra = getattr(msg, "model_extra", None) or {}
    for key in ("reasoning_content", "reasoning"):
        alt = getattr(msg, key, None) or extra.get(key)
        if alt:
            return alt
    return ""


def _create(client, model, system, user, max_tokens, json_mode):
    kwargs = dict(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return client.chat.completions.create(**kwargs)


def complete_json(system: str, user: str, model: str = None, client=None, max_tokens: int = 6000):
    """Returns (parsed_json, receipt, raw_text). Raises ProviderError on real failure.

    Tries response_format={"type":"json_object"} first and retries without it if
    the endpoint rejects the parameter.
    """
    client = client or _client()
    model = model or pick_model(client)
    max_tokens = max(int(max_tokens), MIN_MAX_TOKENS)
    started = time.time()
    resp, json_mode = None, True
    try:
        resp = _create(client, model, system, user, max_tokens, True)
    except Exception as exc:
        if not _REJECTS_JSON_MODE.search(f"{type(exc).__name__}: {exc}"):
            raise ProviderError("PROVIDER_UNAVAILABLE",
                                f"Nosana inference failed: {type(exc).__name__}: {exc}", True)
        json_mode = False
        try:
            resp = _create(client, model, system, user, max_tokens, False)
        except Exception as exc2:  # pragma: no cover - network
            raise ProviderError("PROVIDER_UNAVAILABLE",
                                f"Nosana inference failed: {type(exc2).__name__}: {exc2}", True)
    choice = resp.choices[0]
    text = _message_text(choice)
    usage = resp.usage
    receipt = {
        "model": getattr(resp, "model", model),
        "remote_id": getattr(resp, "id", None),
        "duration_ms": int((time.time() - started) * 1000),
        "json_mode": json_mode,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        } if usage else None,
    }
    if choice.finish_reason == "length":
        _dump_raw(text, "finish_reason=length")
        raise ProviderError(
            "AI_OUTPUT_INVALID",
            f"Nosana output was truncated at max_tokens={max_tokens} (finish_reason=length); "
            "no valid JSON was produced. Raw excerpt saved to .runtime/nosana_last_raw.txt.", True)
    try:
        return _extract_json(text), receipt, text
    except ValueError as exc:
        excerpt = _dump_raw(text, "json_extraction_failed")
        raise ProviderError(
            "AI_OUTPUT_INVALID",
            f"{exc}. Raw excerpt saved to .runtime/nosana_last_raw.txt: "
            f"{excerpt[:300]!r}", True)
