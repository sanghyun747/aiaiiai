"""Clean-room deterministic Instagram follower-diff + audit analyzer.

Self-contained (stdlib only) so it can be uploaded into a Daytona sandbox and
executed there unchanged. No network, no Instagram access, no cause inference.
See PROVENANCE.md: this is a clean-room reimplementation of the contract's
follower invariants, pending replacement by a copy of the original skill.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

VALID_AUDIT_STATUS = {
    "confirmed_rename_still_current_follower",
    "confirmed_rename_relationship_absent",
    "checked_no_confirmed_rename",
    "username_change_not_ruled_out",
}


def _now() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


def _ts(rec):
    t = rec.get("timestamp")
    return t if isinstance(t, int) and t > 0 else None


def _index(records):
    out = {}
    for r in records:
        u = r.get("username")
        if not isinstance(u, str) or not u:
            raise ValueError("INVALID_EXPORT: record without username")
        out[u] = r
    return out


def _window_start(old_records):
    """Comparable window starts at the second-oldest valid timestamp.

    Records older than that are 'outside_window': a single export pair cannot
    prove anything about follows that predate the compared coverage boundary.
    """
    ts = sorted(t for t in (_ts(r) for r in old_records) if t is not None)
    if len(ts) < 2:
        return None
    return ts[1]


def _rename_candidates(old_only, cur_only, old_all, cur_all, pair_is_consecutive, retained):
    """Timestamp-continuity rename linkage. Conservative by construction.

    Requires ALL of: consecutive exports explicitly asserted; at least one
    retained valid-timestamp pair; exact timestamp stability for ALL retained
    valid pairs; candidate timestamp unique in BOTH full exports; exactly one
    old-only/current-only pairing at that timestamp.
    Anything else stays unresolved. Timestamp-only linkage is an
    export-continuity match, never an Instagram identity guarantee.
    """
    reasons = []
    if not pair_is_consecutive:
        return {}, ["exports not asserted consecutive"]
    retained_pairs = [
        (o, c)
        for o, c in retained
        if _ts(o) is not None and _ts(c) is not None
    ]
    if not retained_pairs:
        return {}, ["no comparable retained record with a valid timestamp"]
    if any(_ts(o) != _ts(c) for o, c in retained_pairs):
        return {}, ["retained timestamps unstable across exports"]

    def count(ts, records):
        return sum(1 for r in records if _ts(r) == ts)

    links = {}
    for ou, orec in old_only.items():
        t = _ts(orec)
        if t is None:
            continue
        if count(t, old_all) != 1 or count(t, cur_all) != 1:
            reasons.append("timestamp collision for %s" % ou)
            continue
        matches = [cu for cu, crec in cur_only.items() if _ts(crec) == t]
        if len(matches) != 1:
            reasons.append("no unique current-only pairing for %s" % ou)
            continue
        links[ou] = matches[0]
    return links, reasons


def analyze(case, pair_is_consecutive=None, input_kind="synthetic"):
    """Deterministic diff + mandatory audit layer. Returns a Followers dict."""
    old = case.get("old_followers") or []
    cur = case.get("current_followers") or []
    if not isinstance(old, list) or not isinstance(cur, list):
        raise ValueError("INVALID_EXPORT: follower lists must be arrays")
    consecutive = case.get("pair_is_consecutive", False) if pair_is_consecutive is None else pair_is_consecutive

    old_idx, cur_idx = _index(old), _index(cur)
    old_count, current_count = len(old_idx), len(cur_idx)
    retained_names = sorted(set(old_idx) & set(cur_idx))
    retained = [(old_idx[u], cur_idx[u]) for u in retained_names]
    retained_count = len(retained_names)

    old_only = {u: old_idx[u] for u in sorted(set(old_idx) - set(cur_idx))}
    cur_only = {u: cur_idx[u] for u in sorted(set(cur_idx) - set(old_idx))}
    raw_missing_count = len(old_only)
    raw_new_count = len(cur_only)

    win = _window_start(old)
    links, link_notes = _rename_candidates(old_only, cur_only, old, cur, consecutive, retained)

    cur_following = {r.get("username") for r in (case.get("current_following") or [])}
    inactive = set(case.get("explicitly_inactive") or [])
    supplied_audit = {}
    for a in case.get("trusted_synthetic_audit") or []:
        if input_kind != "synthetic":
            # The fixture's synthetic audit applies ONLY to its own synthetic
            # ZIPs and is never applied to real uploaded records.
            break
        if a.get("status") in VALID_AUDIT_STATUS:
            supplied_audit[a.get("old_username")] = a

    now = _now()
    audits = []
    outside = renamed = absent = unresolved = expl_inactive = 0

    for u, rec in old_only.items():
        t = _ts(rec)
        base = {
            "old_username": u,
            "new_username": None,
            "status": "username_change_not_ruled_out",
            "method": "unresolved",
            "checked_at": now,
            "access_context": "offline_exports",
            "evidence": [],
            "active_evidence": [],
            "relationship_absent": False,
        }
        if win is not None and t is not None and t < win:
            base["status"] = "checked_no_confirmed_rename"
            base["method"] = "unresolved"
            base["evidence"] = [
                "outside comparable window: timestamp %s precedes window start %s" % (t, win)
            ]
            audits.append(base)
            outside += 1
            continue
        if u in inactive:
            base["status"] = "checked_no_confirmed_rename"
            base["evidence"] = ["explicitly marked inactive in supplied export; excluded from loss claims"]
            audits.append(base)
            expl_inactive += 1
            continue
        if u in links:
            new = links[u]
            base["new_username"] = new
            base["status"] = "confirmed_rename_still_current_follower"
            base["method"] = "export_continuity"
            base["evidence"] = [
                "export-continuity match: all retained timestamps stable; %s unique in both full exports" % t
            ]
            base["active_evidence"] = ["current_followers"]
            base["relationship_absent"] = False  # rename statuses ALWAYS imply this
            audits.append(base)
            renamed += 1
            continue
        supplied = supplied_audit.get(u)
        if supplied and supplied.get("status") == "checked_no_confirmed_rename":
            # Relationship absence requires accepted current evidence AND a
            # resolved audit permitting absence. Current-evidence is kept
            # separate from rename resolution.
            has_current_evidence = u in cur_following
            base["status"] = "checked_no_confirmed_rename"
            base["method"] = supplied.get("method", "synthetic_fixture")
            base["access_context"] = supplied.get("access_context", "synthetic_fixture")
            base["evidence"] = list(supplied.get("evidence") or [])
            if has_current_evidence:
                base["active_evidence"] = ["current_following"]
                base["relationship_absent"] = True
                audits.append(base)
                absent += 1
                continue
            audits.append(base)
            unresolved += 1
            continue
        base["evidence"] = ["no stable-ID or accepted public manual audit; %s" % (
            link_notes[0] if link_notes else "no unique export-continuity pairing")]
        audits.append(base)
        unresolved += 1

    followers = {
        "input_kind": input_kind,
        "old_count": old_count,
        "current_count": current_count,
        "export_count_delta": current_count - old_count,
        "retained_count": retained_count,
        "raw_missing_count": raw_missing_count,
        "raw_new_count": raw_new_count,
        "outside_window_count": outside,
        "renamed_still_following_count": renamed,
        "relationship_absent_count": absent,
        "unresolved_count": unresolved,
        "explicitly_inactive_count": expl_inactive,
        "new_observed_excluding_renames": raw_new_count - renamed,
        "audits": audits,
        "scope_note": (
            "내보내기 두 개를 비교한 결정적 결과입니다. 이름 변경 후보는 export 연속성 "
            "일치이며 계정 동일성 증명이 아닙니다. 미해소 항목은 손실로 계산하지 않습니다. "
            "언팔로우 원인은 판단하지 않습니다."
        ),
    }
    check_invariants(followers)
    return followers


def check_invariants(f):
    assert f["raw_missing_count"] == (
        f["outside_window_count"] + f["renamed_still_following_count"]
        + f["relationship_absent_count"] + f["unresolved_count"]
        + f["explicitly_inactive_count"]
    ), "raw_missing partition violated"
    assert f["old_count"] == f["retained_count"] + f["raw_missing_count"], "old_count invariant"
    assert f["current_count"] == f["retained_count"] + f["raw_new_count"], "current_count invariant"
    assert f["export_count_delta"] == f["current_count"] - f["old_count"], "delta invariant"
    assert f["new_observed_excluding_renames"] == f["raw_new_count"] - f["renamed_still_following_count"]
    assert len(f["audits"]) == f["raw_missing_count"], "every candidate needs an audit entry"
    for a in f["audits"]:
        if a["status"] in ("confirmed_rename_still_current_follower", "username_change_not_ruled_out"):
            assert a["relationship_absent"] is False, "rename-uncertain audit cannot claim absence"
    return True


if __name__ == "__main__":
    case = json.load(open(sys.argv[1], encoding="utf-8"))
    out = analyze(case, input_kind=case.get("input_kind", "synthetic"))
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("OK", out["old_count"], out["current_count"], out["retained_count"])
