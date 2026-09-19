"""Nosana prompts. Anonymised aggregates + allowed source ids only.

No usernames, account ids, ZIP contents or raw relationship rows are ever
included. The model cannot manufacture follower counts, observations,
sources, probabilities, revenue or baselines - those are stripped/overwritten
in code after validation.
"""
from __future__ import annotations

import json

GUARD = (
    "당신은 한국어 숏폼 콘텐츠 전략가입니다. 반드시 유효한 JSON 하나만 출력하고 다른 텍스트나 코드펜스를 쓰지 마십시오.\n"
    "금지: 팔로워 수·조회수·관측값·출처·성공 확률·수익·기준값(baseline)을 새로 만들어내는 것. "
    "제공된 source id 목록 밖의 id를 쓰는 것. 도달이나 성장을 보장하는 표현. 언팔로우 원인 단정.\n"
    "모든 수치 주장은 사용자가 직접 측정해 검증해야 하는 가설로 서술하십시오."
)

# Single-line English terminator. The qwen3 reasoning model follows a short
# English instruction far more reliably than a long Korean one.
JSON_ONLY = "Return ONLY one JSON object. No prose, no markdown, no reasoning."


def _anon_sources(sources):
    return [{"id": s["id"], "source_mode": s["source_mode"], "platform": s["platform"],
             "title": s["title"], "views": s.get("views")} for s in sources]


def _anon_followers(followers):
    if not followers:
        return None
    return {k: v for k, v in followers.items() if k not in ("audits", "scope_note")}


def build_plan_prompt(profile, sources, opportunities, followers):
    payload = {
        "profile": {"niche": profile.niche, "audience": profile.audience, "goal": profile.goal,
                    "format": profile.format, "weekly_minutes": profile.weekly_minutes,
                    "query": profile.query},
        "allowed_source_ids": [s["id"] for s in sources],
        "sources": _anon_sources(sources),
        "opportunities": [{"id": o["id"], "title": o["title"], "source_ids": o["source_ids"],
                           "momentum_evidence": o["momentum_evidence"]} for o in opportunities],
        "follower_aggregates": _anon_followers(followers),
    }
    user = (
        "다음 익명 집계를 바탕으로 간단한 전략 계획을 세우십시오.\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n\n출력 JSON 스키마: {\"strengths\":[문자열],\"weaknesses\":[문자열],"
          "\"safe_bet_direction\":문자열,\"growth_experiment_direction\":문자열,"
          "\"weakness_to_target\":문자열}\n"
          "weaknesses는 2~4개, 각 항목은 짧은 명사구입니다.\n\n" + JSON_ONLY
    )
    return GUARD, user


SCHEMA = """{"actions":[{
 "strategy_mode":"safe_bet|growth_experiment",
 "weakness_target":"성장 실험이면 약점 하나의 이름, 안전안이면 null",
 "title":"...","source_ids":["허용된 id"],"fit_reason":"...",
 "hook_a":"...","hook_b":"...","outline":["...","...","..."],"caption":"...",
 "production_minutes":정수,"cta":"...","monetization_hypothesis":"...",
 "metric":"...","baseline":null,"measurement_window_hours":정수,"success_rule":"...",
 "production_package":{
  "script":{"hook":"...","intro":"...","body":["...","...","..."],"ending":"...","cta":"..."},
  "shot_list":[{"order":1,"duration_sec":정수,"visual":"...","narration":"...","subtitle":"..."}],
  "editing_plan":{"pace":"...","caption_style":"...","cut_plan":"...","music_direction":"...","b_roll_notes":["...","..."]},
  "thumbnail_plan":{"concept":"...","text":"...","composition":"...","generation_prompt":"..."},
  "publishing_package":{"title":"...","description":"...","hashtags":["#..."],"cta":"...","target_metric":"...","posting_notes":"..."}
 }}]}"""


def build_recommend_prompt(profile, sources, opportunities, followers, plan):
    payload = {
        "profile": {"niche": profile.niche, "audience": profile.audience, "goal": profile.goal,
                    "format": profile.format, "weekly_minutes": profile.weekly_minutes},
        "allowed_source_ids": [s["id"] for s in sources],
        "sources": _anon_sources(sources),
        "plan": plan,
    }
    user = (
        json.dumps(payload, ensure_ascii=False) + "\n\n"
        "정확히 3개의 action을 담은 JSON을 출력하십시오. 규칙:\n"
        "1) 최소 1개는 strategy_mode=safe_bet, 최소 1개는 strategy_mode=growth_experiment.\n"
        "2) growth_experiment는 weakness_target에 약점 이름 정확히 하나를 적습니다. safe_bet은 null.\n"
        "3) 세 액션의 제목과 검증 가설이 서로 뚜렷이 달라야 합니다(같은 말 바꾸기 금지).\n"
        f"4) production_minutes 합계는 {profile.weekly_minutes} 이하여야 합니다.\n"
        "5) source_ids는 allowed_source_ids 안에서만 고릅니다.\n"
        "6) baseline은 항상 null이고, success_rule은 사용자가 먼저 비교 기준값을 수집하도록 안내합니다.\n"
        "7) shot_list의 order는 1부터 1씩 증가하고 3~6개 샷을 담습니다.\n"
        "8) 모든 액션에 script/shot_list/editing_plan/thumbnail_plan/publishing_package를 빠짐없이 채웁니다.\n"
        "9) music_direction은 설명만 하고 특정 곡이나 라이선스를 제시하지 않습니다.\n\n"
        "스키마:\n" + SCHEMA + "\n\n" + JSON_ONLY
    )
    return GUARD, user


def repair_prompt(system, user, previous_output, error):
    return system, (
        user + "\n\n이전 출력이 아래 이유로 거부되었습니다. 해당 문제만 고쳐 전체 JSON을 다시 출력하십시오.\n"
        f"거부 사유: {error}\n이전 출력(앞부분): {previous_output[:1500]}\n\n" + JSON_ONLY
    )
