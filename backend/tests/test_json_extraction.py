"""Nosana JSON extraction hardening (offline, no network)."""
import json

import pytest

from providers import nosana
from providers.errors import ProviderError


def test_plain_object():
    assert nosana._extract_json('{"a": 1}') == {"a": 1}


def test_strips_think_block_before_json():
    raw = '<think>The user wants JSON. {this brace is unbalanced</think>\n{"ok": true}'
    assert nosana._extract_json(raw) == {"ok": True}


def test_strips_code_fence():
    assert nosana._extract_json('```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


def test_think_block_plus_fence():
    raw = '<think>reasoning...</think>\n```json\n{"actions": []}\n```'
    assert nosana._extract_json(raw) == {"actions": []}


def test_unterminated_think_is_only_a_last_resort():
    """An open <think> must not swallow a payload that follows it."""
    assert nosana._extract_json('<think>hmm {\n{"ok": 1}') == {"ok": 1}


def test_prose_preamble_is_skipped():
    assert nosana._extract_json('Sure! Here is the JSON:\n{"a": 2}\nHope that helps.')["a"] == 2


def test_braces_inside_strings_do_not_break_counting():
    raw = 'x {"a": {"b": "} } not a close"}, "c": 3} y'
    assert nosana._extract_json(raw) == {"a": {"b": "} } not a close"}, "c": 3}


def test_escaped_quote_inside_string():
    assert nosana._extract_json(r'{"a": "he said \"hi\" }"}') == {"a": 'he said "hi" }'}


def test_top_level_array_is_accepted():
    assert nosana._extract_json('junk\n[{"id": 1}]\n') == [{"id": 1}]


def test_first_of_two_objects_wins():
    assert nosana._extract_json('{"a": 1}\n{"b": 2}') == {"a": 1}


def test_unparseable_raises_value_error():
    with pytest.raises(ValueError):
        nosana._extract_json("전혀 JSON 이 아닌 산문입니다.")


def test_raw_dump_is_written_on_failure(tmp_path, monkeypatch):
    dump = tmp_path / "nosana_last_raw.txt"
    monkeypatch.setattr(nosana, "RAW_DUMP", dump)
    nosana._dump_raw("모델이 산문만 반환했습니다" * 50, "json_extraction_failed")
    body = dump.read_text(encoding="utf-8")
    assert "json_extraction_failed" in body
    assert "모델이 산문만 반환했습니다" in body


class _Msg:
    def __init__(self, content=None, **extra):
        self.content = content
        self.model_extra = extra


class _Choice:
    def __init__(self, msg, finish_reason="stop"):
        self.message, self.finish_reason = msg, finish_reason


class _Resp:
    def __init__(self, choice, rid="chatcmpl-test"):
        self.choices, self.id, self.usage, self.model = [choice], rid, None, "qwen/qwen3.8-27b"


class _Completions:
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def create(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class _Client:
    def __init__(self, script):
        self.chat = type("C", (), {"completions": _Completions(script)})()


def _client(script):
    return _Client(script)


def test_content_null_falls_back_to_reasoning_field():
    """Some endpoints return content=null plus a separate reasoning field."""
    c = _client([_Resp(_Choice(_Msg(None, reasoning='{"ok": true}')))])
    data, receipt, raw = nosana.complete_json("s", "u", model="m", client=c)
    assert data == {"ok": True}
    assert receipt["json_mode"] is True


def test_json_object_mode_is_tried_first():
    c = _client([_Resp(_Choice(_Msg('{"a": 1}')))])
    nosana.complete_json("s", "u", model="m", client=c)
    assert c.chat.completions.calls[0]["response_format"] == {"type": "json_object"}


def test_falls_back_when_endpoint_rejects_response_format():
    c = _client([ValueError("400 unsupported parameter: response_format"),
                 _Resp(_Choice(_Msg('{"a": 1}')))])
    data, receipt, _ = nosana.complete_json("s", "u", model="m", client=c)
    assert data == {"a": 1}
    assert receipt["json_mode"] is False
    assert "response_format" not in c.chat.completions.calls[1]


def test_unrelated_transport_error_is_not_retried_without_json_mode():
    c = _client([RuntimeError("connection reset by peer")])
    with pytest.raises(ProviderError) as exc:
        nosana.complete_json("s", "u", model="m", client=c)
    assert exc.value.code == "PROVIDER_UNAVAILABLE"
    assert len(c.chat.completions.calls) == 1


def test_max_tokens_floor_is_enforced():
    """A small budget makes the reasoning model spend everything on reasoning."""
    c = _client([_Resp(_Choice(_Msg('{"a": 1}')))])
    nosana.complete_json("s", "u", model="m", client=c, max_tokens=200)
    assert c.chat.completions.calls[0]["max_tokens"] == nosana.MIN_MAX_TOKENS


def test_truncation_raises_ai_output_invalid(tmp_path, monkeypatch):
    monkeypatch.setattr(nosana, "RAW_DUMP", tmp_path / "raw.txt")
    c = _client([_Resp(_Choice(_Msg('{"a": '), finish_reason="length"))])
    with pytest.raises(ProviderError) as exc:
        nosana.complete_json("s", "u", model="m", client=c)
    assert exc.value.code == "AI_OUTPUT_INVALID"


def test_unparseable_output_dumps_raw_and_raises(tmp_path, monkeypatch):
    dump = tmp_path / "raw.txt"
    monkeypatch.setattr(nosana, "RAW_DUMP", dump)
    c = _client([_Resp(_Choice(_Msg("죄송합니다, JSON 을 만들 수 없습니다.")))])
    with pytest.raises(ProviderError) as exc:
        nosana.complete_json("s", "u", model="m", client=c)
    assert exc.value.code == "AI_OUTPUT_INVALID"
    assert "nosana_last_raw.txt" in exc.value.message
    assert "JSON 을 만들 수 없습니다" in dump.read_text(encoding="utf-8")


def test_prompts_end_with_single_line_english_json_instruction():
    from app import prompts
    from app.models import Profile
    profile = Profile.model_validate(json.loads(
        (nosana.RAW_DUMP.parent.parent.parent / "fixtures" / "profile-sample.json")
        .read_text(encoding="utf-8")))
    sources = [{"id": "s1", "source_mode": "synthetic", "platform": "synthetic",
                "title": "t", "views": 1}]
    opps = [{"id": "o1", "title": "t", "source_ids": ["s1"], "momentum_evidence": "single_observation"}]
    for _, user in (prompts.build_plan_prompt(profile, sources, opps, None),
                    prompts.build_recommend_prompt(profile, sources, opps, None, {})):
        assert user.rstrip().endswith(prompts.JSON_ONLY)
    assert "\n" not in prompts.JSON_ONLY
