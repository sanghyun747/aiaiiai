"""Labelled demo-replay path: Nosana plan/recommend come from the fixture,
Daytona analyze + render still execute for real. Opt-in only."""
import json
from pathlib import Path

import pytest

from app import config, pipeline, worker
from app.models import Profile
from app.store import RunState
from providers import youtube

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures"


@pytest.fixture
def profile():
    return Profile.model_validate(json.loads(
        (FIXTURES / "profile-sample.json").read_text(encoding="utf-8")))


@pytest.fixture
def run():
    return RunState("run_replay_test", "fp")


def _sources(profile):
    return youtube.synthetic_sources(profile.query)


# ------------------------------------------------------------ opt-in gate
def test_replay_is_off_by_default(monkeypatch):
    monkeypatch.delenv("TRENDPILOT_LIVE_PROVIDERS", raising=False)
    assert config.replay_mode_enabled() is False
    assert config.live_providers_enabled() is True


def test_replay_requires_explicit_zero(monkeypatch):
    monkeypatch.setenv("TRENDPILOT_LIVE_PROVIDERS", "0")
    assert config.replay_mode_enabled() is True
    assert config.live_providers_enabled() is False


@pytest.mark.parametrize("value", ["", "false", "off", "2", "no"])
def test_other_values_enable_neither_replay_nor_live(monkeypatch, value):
    """A typo must not silently turn the demo path on."""
    monkeypatch.setenv("TRENDPILOT_LIVE_PROVIDERS", value)
    assert config.replay_mode_enabled() is False
    assert config.live_providers_enabled() is False


def test_live_failure_never_falls_back_to_replay(monkeypatch, profile, run):
    """A live provider error must end the run, not quietly serve the fixture."""
    monkeypatch.setenv("TRENDPILOT_LIVE_PROVIDERS", "1")

    def boom(*a, **k):
        raise RuntimeError("nosana down")

    monkeypatch.setattr(worker.nosana, "_client", boom)
    worker.execute(run, profile, None)
    assert run.status == "failed"
    assert run.is_mock is False
    assert run.result is None


# ---------------------------------------------------------------- content
def test_replay_actions_satisfy_the_contract(profile):
    sources = _sources(profile)
    actions = pipeline.load_replay_actions(profile, sources)
    assert len(actions) == 3
    modes = {a.strategy_mode for a in actions}
    assert "safe_bet" in modes and "growth_experiment" in modes
    for a in actions:
        if a.strategy_mode == "growth_experiment":
            assert a.weakness_target
        else:
            assert a.weakness_target is None
        assert a.baseline is None
        orders = [s.order for s in a.production_package.shot_list]
        assert orders == list(range(1, len(orders) + 1))
    assert sum(a.production_minutes for a in actions) <= profile.weekly_minutes


def test_replay_actions_only_use_allowed_source_ids(profile):
    sources = _sources(profile)
    allowed = {s["id"] for s in sources}
    for a in pipeline.load_replay_actions(profile, sources):
        assert set(a.source_ids) <= allowed


def test_replay_stages_are_traced_as_replay_not_live(profile, run):
    sources = _sources(profile)
    plan = pipeline.stage_plan_replay(run, profile)
    pipeline.stage_recommend_replay(run, profile, sources)
    assert plan["source"] == "fixtures/run-sample.json"
    modes = {(t["operation"], t["mode"]) for t in run.trace}
    assert ("plan", "replay") in modes and ("recommend", "replay") in modes
    assert not any(t["mode"] == "live" and t["provider"] == "nosana" for t in run.trace)
    for t in run.trace:
        assert "run-sample.json" in t["detail"]


def test_replay_notice_and_limitation_say_it_is_not_live_inference():
    assert "실시간" in config.REPLAY_NOTICE or "아닙니다" in config.REPLAY_NOTICE
    assert "Daytona" in config.REPLAY_NOTICE
    assert "replay" in worker.REPLAY_LIMITATION


# ----------------------------------------------------- end-to-end (stubbed
# Daytona; the point is that analyze/render still go through the sandbox path)
class _FakeSandbox:
    sandbox_id = "sbx-fake"

    def __init__(self):
        self.execs = []

    def start(self):
        return self

    def exec(self, cmd, timeout=None):
        self.execs.append(cmd)
        return 0, ""

    def upload(self, local, remote):
        pass

    def download(self, remote):
        import hashlib
        if remote.endswith("followers.json"):
            case = json.loads((FIXTURES / "follower-case.json").read_text(encoding="utf-8"))
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor" / "follower_diff"))
            import analyzer
            case["pair_is_consecutive"] = True
            case["input_kind"] = "synthetic"
            return json.dumps(analyzer.analyze(case), ensure_ascii=False).encode("utf-8")
        if remote.endswith("manifest.json"):
            self._files = {n: f"# {n}\n".encode("utf-8") for n in config.ARTIFACT_NAMES}
            return json.dumps([
                {"name": n, "sha256": hashlib.sha256(b).hexdigest()}
                for n, b in self._files.items()]).encode("utf-8")
        return self._files[remote.rsplit("/", 1)[-1]]

    def stop(self):
        return "deleted"


def test_replay_run_reaches_succeeded_with_real_sandbox_stages(monkeypatch, profile, run):
    monkeypatch.setenv("TRENDPILOT_LIVE_PROVIDERS", "0")

    def no_nosana(*a, **k):
        raise AssertionError("replay mode must never call Nosana")

    monkeypatch.setattr(worker.nosana, "_client", no_nosana)
    monkeypatch.setattr(worker.nosana, "pick_model", no_nosana)
    monkeypatch.setattr(worker.daytona_sandbox, "DaytonaRun", _FakeSandbox)

    worker.execute(run, profile, None)

    assert run.status == "succeeded", run.error
    assert run.stage == "done"
    assert run.is_mock is True
    assert run.result.sample_notice == config.REPLAY_NOTICE
    assert worker.REPLAY_LIMITATION in run.result.limitations
    assert len(run.result.actions) == 3
    assert {a.name for a in run.result.artifacts} == set(config.ARTIFACT_NAMES)
    ops = {(t["provider"], t["operation"], t["mode"]) for t in run.trace}
    # Daytona stages are NOT replayed.
    assert ("daytona", "analyze", "live") in ops
    assert ("daytona", "render", "live") in ops
    assert ("nosana", "plan", "replay") in ops
