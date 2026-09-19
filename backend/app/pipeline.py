"""Run pipeline: validate -> plan -> analyze -> recommend -> render -> done.

Every stage transition reflects work that actually completed. No timers.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import exports
from .config import ARTIFACT_NAMES, BASE_DIR, RUNTIME_DIR
from .models import Action, Followers, Result
from .prompts import build_plan_prompt, build_recommend_prompt, repair_prompt
from providers import daytona_sandbox, nosana, youtube
from providers.errors import ProviderError

sys.path.insert(0, str(BASE_DIR / "vendor" / "follower_diff"))
import analyzer  # noqa: E402  (vendored clean-room analyzer)

KST = timezone(timedelta(hours=9))
FIXTURES = BASE_DIR.parent / "fixtures"


def now() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


class StageFailure(Exception):
    def __init__(self, code, message, retryable=False, partial=False):
        super().__init__(message)
        self.code, self.message, self.retryable, self.partial = code, message, retryable, partial


def _trace(run, provider, operation, mode, status, **kw):
    run.add_trace({
        "provider": provider, "operation": operation, "mode": mode, "status": status,
        "remote_id": kw.get("remote_id"), "executed_at": kw.get("executed_at") or now(),
        "duration_ms": kw.get("duration_ms"), "artifact_sha256": kw.get("artifact_sha256"),
        "detail": kw.get("detail", ""),
    })


# ----------------------------------------------------------------- validate
def stage_validate(run, profile, uploads):
    run.set_stage("validate")
    rundir = RUNTIME_DIR / run.run_id
    rundir.mkdir(parents=True, exist_ok=True)
    if profile.sample_followers:
        case = json.loads((FIXTURES / "follower-case.json").read_text(encoding="utf-8"))
        exports.write_synthetic_pair(case, rundir)
        case["pair_is_consecutive"] = profile.pair_is_consecutive
        return {"case": case, "input_kind": "synthetic"}
    if not uploads:
        return None  # followers stays null; this is NOT a zero-loss result
    old = exports.parse_export(uploads["old"])
    cur = exports.parse_export(uploads["current"])
    case = {
        "old_followers": exports.minimize(old["followers"]),
        "current_followers": exports.minimize(cur["followers"]),
        "old_following": exports.minimize(old["following"]),
        "current_following": exports.minimize(cur["following"]),
        "pair_is_consecutive": profile.pair_is_consecutive,
    }
    return {"case": case, "input_kind": "user_upload"}


# --------------------------------------------------------------- evidence
def collect_sources(run, profile):
    if youtube.is_configured() and profile.data_mode == "live":
        try:
            started = time.time()
            rows = youtube.search_sources(profile.query)
            _trace(run, "youtube", "search", "live", "success",
                   duration_ms=int((time.time() - started) * 1000),
                   detail="YouTube Data API 단일 관측.")
            if rows:
                return rows, "live"
        except ProviderError as exc:
            _trace(run, "youtube", "search", "live", "failed", detail=exc.message)
    _trace(run, "youtube", "search", "mock", "skipped",
           detail="YOUTUBE_API_KEY 미설정. 합성 근거를 사용하며 실시간 수집이 아닙니다.")
    return youtube.synthetic_sources(profile.query), "synthetic"


def build_opportunities(sources):
    out = []
    observed = datetime.fromisoformat(sources[0]["observed_at"]) if sources else None
    for i, s in enumerate(sources, start=1):
        mvph = None
        if s.get("views") is not None and s.get("published_at") and observed is not None:
            try:
                hours = (observed - datetime.fromisoformat(s["published_at"])).total_seconds() / 3600.0
                if hours > 0:
                    mvph = round(s["views"] / hours, 2)
            except ValueError:
                mvph = None
        out.append({
            "id": f"opp-{i}", "title": s["title"], "source_ids": [s["id"]],
            "reason": "단일 관측 기준 기술적 평균입니다. 성장 속도·가속·유행 순위가 아닙니다.",
            "mean_views_per_hour": mvph, "momentum_evidence": "single_observation",
        })
    return out


# ------------------------------------------------------------------- plan
def stage_plan(run, profile, sources, opportunities, followers, client, model):
    run.set_stage("plan")
    system, user = build_plan_prompt(profile, sources, opportunities, followers)
    plan, receipt, _ = nosana.complete_json(system, user, model=model, client=client, max_tokens=1500)
    _trace(run, "nosana", "plan", "live", "success", remote_id=receipt["remote_id"],
           duration_ms=receipt["duration_ms"],
           detail=f"model={receipt['model']} usage={json.dumps(receipt['usage'])}")
    run.receipts.append({"stage": "plan", **receipt})
    return plan


# ---------------------------------------------------------------- analyze
def stage_analyze(run, sandbox, follower_input):
    """Deterministic follower analysis executed inside the Daytona sandbox."""
    run.set_stage("analyze")
    if follower_input is None:
        _trace(run, "daytona", "analyze", "live", "skipped",
               detail="팔로워 입력 없음. followers=null (손실 0이라는 뜻이 아닙니다).")
        return None
    rundir = RUNTIME_DIR / run.run_id
    case_path = rundir / "analysis_input.json"
    payload = dict(follower_input["case"])
    payload["input_kind"] = follower_input["input_kind"]
    payload["old_followers"] = exports.minimize(payload["old_followers"])
    payload["current_followers"] = exports.minimize(payload["current_followers"])
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    sandbox.upload(str(BASE_DIR / "vendor" / "follower_diff" / "analyzer.py"), "/tmp/tp/analyzer.py")
    sandbox.upload(str(case_path), "/tmp/tp/case.json")
    started = time.time()
    code, out = sandbox.exec("cd /tmp/tp && python3 analyzer.py case.json followers.json", timeout=120)
    if code != 0:
        raise StageFailure("PROVIDER_UNAVAILABLE", f"Daytona analyze exited {code}: {out.strip()[:300]}", True)
    raw = sandbox.download("/tmp/tp/followers.json")
    followers = json.loads(raw.decode("utf-8"))
    analyzer.check_invariants(followers)  # re-verified locally
    _trace(run, "daytona", "analyze", "live", "success", remote_id=sandbox.sandbox_id,
           duration_ms=int((time.time() - started) * 1000),
           artifact_sha256=hashlib.sha256(raw).hexdigest(),
           detail="샌드박스에서 결정적 팔로워 diff/감사 실행. 로컬에서 불변식 재검증.")
    return followers


# -------------------------------------------------------------- recommend
def _validate_actions(raw_actions, profile, source_ids):
    if not isinstance(raw_actions, list) or len(raw_actions) != 3:
        raise ValueError("exactly three actions are required, got %s" % (
            len(raw_actions) if isinstance(raw_actions, list) else type(raw_actions).__name__))
    actions, titles = [], set()
    for i, raw in enumerate(raw_actions, start=1):
        if not isinstance(raw, dict):
            raise ValueError("action %d is not an object" % i)
        raw = dict(raw)
        raw.setdefault("id", f"act-{i}")
        raw["id"] = f"act-{i}"
        raw["baseline"] = None  # the model may never invent a baseline
        unknown = [s for s in (raw.get("source_ids") or []) if s not in source_ids]
        if unknown:
            raise ValueError("unknown source_id(s): %s" % ", ".join(map(str, unknown)))
        action = Action.model_validate(raw)
        if action.strategy_mode == "growth_experiment" and not action.weakness_target:
            raise ValueError("a growth_experiment must name exactly one weakness_target")
        if action.strategy_mode == "safe_bet":
            action.weakness_target = None
        orders = [s.order for s in action.production_package.shot_list]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("shot_list order must be 1..n ascending, got %s" % orders)
        key = action.title.strip()
        if key in titles:
            raise ValueError("duplicate action title; three paraphrases are not three experiments")
        titles.add(key)
        actions.append(action)
    modes = {a.strategy_mode for a in actions}
    if "safe_bet" not in modes:
        raise ValueError("at least one safe_bet is required")
    if "growth_experiment" not in modes:
        raise ValueError("at least one growth_experiment is required")
    total = sum(a.production_minutes for a in actions)
    if total > profile.weekly_minutes:
        raise ValueError("sum(production_minutes)=%d exceeds weekly_minutes=%d" % (total, profile.weekly_minutes))
    return actions


def stage_recommend(run, profile, sources, opportunities, followers, plan, client, model):
    run.set_stage("recommend")
    source_ids = {s["id"] for s in sources}
    system, user = build_recommend_prompt(profile, sources, opportunities, followers, plan)
    data, receipt, text = nosana.complete_json(system, user, model=model, client=client, max_tokens=8000)
    run.receipts.append({"stage": "recommend", **receipt})
    try:
        actions = _validate_actions(data.get("actions") if isinstance(data, dict) else data,
                                    profile, source_ids)
    except (ValueError, Exception) as first:
        # Exactly one repair attempt, then fail honestly.
        _trace(run, "nosana", "recommend", "live", "failed",
               remote_id=receipt["remote_id"], duration_ms=receipt["duration_ms"],
               detail=f"1차 출력 검증 실패: {str(first)[:250]}")
        sys2, user2 = repair_prompt(system, user, text, str(first))
        data2, receipt2, _ = nosana.complete_json(sys2, user2, model=model, client=client, max_tokens=8000)
        run.receipts.append({"stage": "recommend_repair", **receipt2})
        try:
            actions = _validate_actions(data2.get("actions") if isinstance(data2, dict) else data2,
                                        profile, source_ids)
        except Exception as second:
            _trace(run, "nosana", "recommend_repair", "live", "failed",
                   remote_id=receipt2["remote_id"], duration_ms=receipt2["duration_ms"],
                   detail=f"수리 후에도 검증 실패: {str(second)[:250]}")
            raise StageFailure("AI_OUTPUT_INVALID",
                               f"Nosana output failed validation after one repair: {second}", False, partial=True)
        receipt = receipt2
        _trace(run, "nosana", "recommend_repair", "live", "success", remote_id=receipt2["remote_id"],
               duration_ms=receipt2["duration_ms"],
               detail=f"model={receipt2['model']} usage={json.dumps(receipt2['usage'])}")
        return actions
    _trace(run, "nosana", "recommend", "live", "success", remote_id=receipt["remote_id"],
           duration_ms=receipt["duration_ms"],
           detail=f"model={receipt['model']} usage={json.dumps(receipt['usage'])}")
    return actions


# ------------------------------------------------------------------ render
def stage_render(run, sandbox, payload):
    run.set_stage("render")
    rundir = RUNTIME_DIR / run.run_id
    artdir = rundir / "artifacts"
    artdir.mkdir(parents=True, exist_ok=True)
    payload_path = rundir / "render_payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    sandbox.upload(str(BASE_DIR / "app" / "sandbox" / "render_artifacts.py"), "/tmp/tp/render_artifacts.py")
    sandbox.upload(str(payload_path), "/tmp/tp/payload.json")
    started = time.time()
    code, out = sandbox.exec("cd /tmp/tp && python3 render_artifacts.py payload.json out", timeout=120)
    if code != 0:
        raise StageFailure("PROVIDER_UNAVAILABLE", f"Daytona render exited {code}: {out.strip()[:300]}", True)
    manifest = json.loads(sandbox.download("/tmp/tp/out/manifest.json").decode("utf-8"))
    verified = []
    for entry in manifest:
        name = entry["name"]
        if name not in ARTIFACT_NAMES:
            continue  # allowlist only
        data = sandbox.download(f"/tmp/tp/out/{name}")
        local_sha = hashlib.sha256(data).hexdigest()
        if local_sha != entry["sha256"]:
            continue  # only verified files are listed
        (artdir / name).write_bytes(data)
        verified.append({"name": name, "path": f"artifacts/{name}", "sha256": local_sha})
    _trace(run, "daytona", "render", "live", "success", remote_id=sandbox.sandbox_id,
           duration_ms=int((time.time() - started) * 1000),
           artifact_sha256=next((v["sha256"] for v in verified if v["name"] == "report.md"), None),
           detail="샌드박스에서 고정 템플릿으로 %d개 산출물 생성 후 SHA-256 로컬 검증." % len(verified))
    return verified
