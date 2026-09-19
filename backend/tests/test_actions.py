"""Action/production-package validation — pure, no network."""
import copy

import pytest
from app.models import Profile
from app.pipeline import _validate_actions

PROFILE = Profile(niche="n", audience="a", goal="followers", format="instagram_reel",
                  weekly_minutes=120, query="q", data_mode="demo", sample_followers=True,
                  pair_is_consecutive=True, cloud_processing_consent=False)
SOURCE_IDS = {"syn-s1", "syn-s2", "syn-s3"}


def pkg():
    return {
        "script": {"hook": "h", "intro": "i", "body": ["b1", "b2"], "ending": "e", "cta": "c"},
        "shot_list": [
            {"order": 1, "duration_sec": 4, "visual": "v", "narration": "n", "subtitle": "s"},
            {"order": 2, "duration_sec": 8, "visual": "v", "narration": "n", "subtitle": "s"},
        ],
        "editing_plan": {"pace": "p", "caption_style": "cs", "cut_plan": "cp",
                         "music_direction": "md", "b_roll_notes": ["b"]},
        "thumbnail_plan": {"concept": "c", "text": "t", "composition": "co", "generation_prompt": "g"},
        "publishing_package": {"title": "t", "description": "d", "hashtags": ["#x"], "cta": "c",
                               "target_metric": "m", "posting_notes": "p"},
    }


def action(i, mode="safe_bet", weakness=None, minutes=30, src="syn-s1"):
    return {"strategy_mode": mode, "weakness_target": weakness, "title": f"t{i}",
            "source_ids": [src], "fit_reason": "f", "hook_a": "a", "hook_b": "b",
            "outline": ["o"], "caption": "c", "production_minutes": minutes, "cta": "c",
            "monetization_hypothesis": "m", "metric": "mm", "baseline": None,
            "measurement_window_hours": 72, "success_rule": "s", "production_package": pkg()}


def good():
    return [action(1), action(2, "growth_experiment", "짧은 도입부"), action(3)]


def test_valid_set_passes():
    actions = _validate_actions(good(), PROFILE, SOURCE_IDS)
    assert len(actions) == 3
    assert [a.id for a in actions] == ["act-1", "act-2", "act-3"]


def test_exactly_three_actions_required():
    with pytest.raises(ValueError, match="exactly three"):
        _validate_actions(good()[:2], PROFILE, SOURCE_IDS)
    with pytest.raises(ValueError, match="exactly three"):
        _validate_actions(good() + [action(4)], PROFILE, SOURCE_IDS)


def test_safe_bet_required():
    raw = [action(1, "growth_experiment", "w1"), action(2, "growth_experiment", "w2"),
           action(3, "growth_experiment", "w3")]
    with pytest.raises(ValueError, match="safe_bet"):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_growth_experiment_required():
    with pytest.raises(ValueError, match="growth_experiment"):
        _validate_actions([action(1), action(2), action(3)], PROFILE, SOURCE_IDS)


def test_growth_experiment_needs_weakness_target():
    raw = good()
    raw[1]["weakness_target"] = None
    with pytest.raises(ValueError, match="weakness_target"):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_safe_bet_weakness_is_cleared():
    raw = good()
    raw[0]["weakness_target"] = "모델이 임의로 채운 값"
    assert _validate_actions(raw, PROFILE, SOURCE_IDS)[0].weakness_target is None


def test_unknown_source_id_rejected():
    raw = good()
    raw[0]["source_ids"] = ["made-up-source"]
    with pytest.raises(ValueError, match="unknown source_id"):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_time_budget_enforced():
    raw = [action(1, minutes=60), action(2, "growth_experiment", "w", minutes=60),
           action(3, minutes=60)]
    with pytest.raises(ValueError, match="exceeds weekly_minutes"):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_shot_list_order_must_be_sequential():
    raw = good()
    raw[0]["production_package"]["shot_list"][1]["order"] = 5
    with pytest.raises(ValueError, match="order"):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_duplicate_titles_rejected():
    raw = good()
    raw[2]["title"] = raw[0]["title"]
    with pytest.raises(ValueError, match="duplicate"):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_incomplete_production_package_rejected():
    raw = good()
    del raw[0]["production_package"]["thumbnail_plan"]
    with pytest.raises(Exception):
        _validate_actions(raw, PROFILE, SOURCE_IDS)


def test_model_cannot_invent_a_baseline():
    raw = good()
    raw[0]["baseline"] = 12345.0
    assert _validate_actions(raw, PROFILE, SOURCE_IDS)[0].baseline is None


def test_empty_shot_list_rejected():
    raw = good()
    raw[0]["production_package"]["shot_list"] = []
    with pytest.raises(Exception):
        _validate_actions(raw, PROFILE, SOURCE_IDS)
