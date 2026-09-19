"""Follower invariants + rename/unresolved negatives (no network)."""
import copy

import analyzer
import pytest


def test_fixture_expectations_match(follower_case):
    f = analyzer.analyze(follower_case)
    for key, expected in follower_case["expected"].items():
        assert f[key] == expected, key


def test_partition_and_count_invariants(follower_case):
    f = analyzer.analyze(follower_case)
    assert f["raw_missing_count"] == (
        f["outside_window_count"] + f["renamed_still_following_count"]
        + f["relationship_absent_count"] + f["unresolved_count"] + f["explicitly_inactive_count"])
    assert f["old_count"] == f["retained_count"] + f["raw_missing_count"]
    assert f["current_count"] == f["retained_count"] + f["raw_new_count"]
    assert f["export_count_delta"] == f["current_count"] - f["old_count"]
    assert len(f["audits"]) == f["raw_missing_count"]


def test_every_candidate_has_an_audit_entry(follower_case):
    f = analyzer.analyze(follower_case)
    olds = {r["username"] for r in follower_case["old_followers"]}
    currents = {r["username"] for r in follower_case["current_followers"]}
    assert {a["old_username"] for a in f["audits"]} == olds - currents


def test_nonconsecutive_pair_blocks_rename(follower_case):
    case = copy.deepcopy(follower_case)
    case["pair_is_consecutive"] = False
    f = analyzer.analyze(case, pair_is_consecutive=False)
    assert f["renamed_still_following_count"] == 0
    assert f["unresolved_count"] >= 2
    assert all(a["status"] != "confirmed_rename_still_current_follower" for a in f["audits"])


def test_unstable_retained_timestamps_block_rename(follower_case):
    case = copy.deepcopy(follower_case)
    case["current_followers"][0]["timestamp"] += 7  # retained pair drifts
    f = analyzer.analyze(case)
    assert f["renamed_still_following_count"] == 0


def test_timestamp_collision_stays_unresolved(follower_case):
    case = copy.deepcopy(follower_case)
    # duplicate the rename candidate's timestamp elsewhere in the current export
    case["current_followers"].append({"username": "tp_collide", "timestamp": 1700000030})
    f = analyzer.analyze(case)
    assert f["renamed_still_following_count"] == 0
    assert any(a["status"] == "username_change_not_ruled_out" for a in f["audits"])


def test_rename_and_uncertain_never_claim_absence(follower_case):
    f = analyzer.analyze(follower_case)
    for a in f["audits"]:
        if a["status"] in ("confirmed_rename_still_current_follower", "username_change_not_ruled_out"):
            assert a["relationship_absent"] is False


def test_relationship_absent_requires_current_evidence(follower_case):
    case = copy.deepcopy(follower_case)
    case["current_following"] = []      # remove the accepted current evidence
    f = analyzer.analyze(case)
    assert f["relationship_absent_count"] == 0
    assert f["unresolved_count"] == 2


def test_synthetic_audit_never_applies_to_user_upload(follower_case):
    f = analyzer.analyze(follower_case, input_kind="user_upload")
    assert f["input_kind"] == "user_upload"
    assert f["relationship_absent_count"] == 0  # fixture audit is ignored for real uploads


def test_record_without_username_is_rejected(follower_case):
    case = copy.deepcopy(follower_case)
    case["old_followers"].append({"timestamp": 1700000099})
    with pytest.raises(ValueError):
        analyzer.analyze(case)
