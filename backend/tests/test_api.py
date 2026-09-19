"""HTTP contract, auth, idempotency, artifact allowlist, publish, privacy.

Providers are stubbed; no network. One optional live test is env-gated.
"""
import hashlib
import json
import os
import uuid
from pathlib import Path

import pytest
from app import worker
from app.config import CONTRACT_VERSION
from app.models import Profile
from app.report_html import render_public_html
from app.store import STORE


def key():
    return str(uuid.uuid4())


def form(profile_dict, **over):
    p = dict(profile_dict)
    p.update(over)
    return {"profile_json": json.dumps(p, ensure_ascii=False)}


# ------------------------------------------------------------------ health
def test_health_reports_key_presence_only(client):
    body = client.get("/api/v1/health").json()
    assert body["contract_version"] == CONTRACT_VERSION
    assert set(body["configured"]) == {"nosana", "daytona", "dnsimple", "youtube"}
    assert all(isinstance(v, bool) for v in body["configured"].values())


# ------------------------------------------------------------------ create
def test_create_requires_idempotency_key(client, profile_dict):
    r = client.post("/api/v1/runs", data=form(profile_dict))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_PROFILE"


def test_invalid_profile_rejected(client):
    r = client.post("/api/v1/runs", data={"profile_json": '{"niche":"only"}'},
                    headers={"Idempotency-Key": key()})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_PROFILE"


def test_accepted_shape(client, profile_dict, monkeypatch):
    monkeypatch.setattr(worker, "submit", lambda *a, **k: None)
    r = client.post("/api/v1/runs", data=form(profile_dict), headers={"Idempotency-Key": key()})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued" and body["contract_version"] == CONTRACT_VERSION
    assert len(body["access_token"]) >= 20


def test_idempotency_reuse_and_conflict(client, profile_dict, monkeypatch):
    monkeypatch.setattr(worker, "submit", lambda *a, **k: None)
    k = key()
    first = client.post("/api/v1/runs", data=form(profile_dict), headers={"Idempotency-Key": k}).json()
    again = client.post("/api/v1/runs", data=form(profile_dict), headers={"Idempotency-Key": k}).json()
    assert again["run_id"] == first["run_id"]
    conflict = client.post("/api/v1/runs", data=form(profile_dict, weekly_minutes=300),
                           headers={"Idempotency-Key": k})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_sample_followers_rejects_uploads(client, profile_dict, tmp_path):
    z = tmp_path / "x.zip"
    z.write_bytes(b"PK\x03\x04")
    with open(z, "rb") as fh:
        r = client.post("/api/v1/runs", data=form(profile_dict, sample_followers=True),
                        files={"old_export": ("old.zip", fh, "application/zip")},
                        headers={"Idempotency-Key": key()})
    assert r.status_code == 422


def test_single_export_is_incomplete_pair(client, profile_dict, tmp_path):
    z = tmp_path / "x.zip"
    z.write_bytes(b"PK\x03\x04")
    with open(z, "rb") as fh:
        r = client.post("/api/v1/runs",
                        data=form(profile_dict, sample_followers=False, cloud_processing_consent=True),
                        files={"old_export": ("old.zip", fh, "application/zip")},
                        headers={"Idempotency-Key": key()})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INCOMPLETE_EXPORT_PAIR"


def test_upload_without_consent_rejected(client, profile_dict, follower_case, tmp_path):
    from app import exports
    paths = exports.write_synthetic_pair(follower_case, tmp_path)
    with open(paths["old"], "rb") as a, open(paths["current"], "rb") as b:
        r = client.post("/api/v1/runs",
                        data=form(profile_dict, sample_followers=False, cloud_processing_consent=False),
                        files={"old_export": ("o.zip", a, "application/zip"),
                               "current_export": ("c.zip", b, "application/zip")},
                        headers={"Idempotency-Key": key()})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_malformed_zip_upload_rejected(client, profile_dict, tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"definitely not a zip")
    with open(bad, "rb") as a, open(bad, "rb") as b:
        r = client.post("/api/v1/runs",
                        data=form(profile_dict, sample_followers=False, cloud_processing_consent=True),
                        files={"old_export": ("o.zip", a, "application/zip"),
                               "current_export": ("c.zip", b, "application/zip")},
                        headers={"Idempotency-Key": key()})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_ZIP"


# -------------------------------------------------------------- auth/token
def _queued(client, profile_dict, monkeypatch):
    monkeypatch.setattr(worker, "submit", lambda *a, **k: None)
    body = client.post("/api/v1/runs", data=form(profile_dict), headers={"Idempotency-Key": key()}).json()
    return STORE.get(body["run_id"]), body["access_token"]


def test_get_run_requires_token(client, profile_dict, monkeypatch):
    run, token = _queued(client, profile_dict, monkeypatch)
    assert client.get(f"/api/v1/runs/{run.run_id}").status_code == 401
    assert client.get(f"/api/v1/runs/{run.run_id}",
                      headers={"Authorization": "Bearer wrong-token-value"}).status_code == 401
    ok = client.get(f"/api/v1/runs/{run.run_id}", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200 and ok.json()["status"] == "queued"


def test_unknown_run_is_404(client):
    r = client.get("/api/v1/runs/run_does_not_exist", headers={"Authorization": "Bearer x"})
    assert r.status_code == 404


def test_tokens_differ_between_runs(client, profile_dict, monkeypatch):
    a, ta = _queued(client, profile_dict, monkeypatch)
    b, tb = _queued(client, profile_dict, monkeypatch)
    assert ta != tb
    assert client.get(f"/api/v1/runs/{b.run_id}",
                      headers={"Authorization": f"Bearer {ta}"}).status_code == 401


# ---------------------------------------------------------------- artifacts
def _finish(run, tmp_path):
    from tests.test_actions import PROFILE, good
    from app.models import Result
    from app.pipeline import _validate_actions
    from providers.youtube import synthetic_sources
    sources = synthetic_sources("q")
    actions = _validate_actions(good(), PROFILE, {s["id"] for s in sources})
    for a in actions:
        a.source_ids = [sources[0]["id"]]
    data = b"# report\n"
    path = tmp_path / "report.md"
    path.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    run.artifacts = {"report.md": path}
    run.result = Result(evidence_mode="synthetic", sample_notice="합성", sources=sources,
                        opportunities=[], followers=None, actions=actions,
                        limitations=["합성 데이터"],
                        artifacts=[{"name": "report.md", "path": "artifacts/report.md", "sha256": sha}])
    run.status, run.stage = "succeeded", "done"
    return sha


def test_report_download_is_attachment(client, profile_dict, monkeypatch, tmp_path):
    run, token = _queued(client, profile_dict, monkeypatch)
    sha = _finish(run, tmp_path)
    r = client.get(f"/api/v1/runs/{run.run_id}/artifacts/report.md",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert hashlib.sha256(r.content).hexdigest() == sha


def test_artifact_allowlist_blocks_traversal_and_unlisted(client, profile_dict, monkeypatch, tmp_path):
    run, token = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    h = {"Authorization": f"Bearer {token}"}
    for name in ("script.md", "..%2F..%2Fetc%2Fpasswd", "secrets.env", ".env"):
        assert client.get(f"/api/v1/runs/{run.run_id}/artifacts/{name}", headers=h).status_code in (404, 400)


def test_artifact_requires_token(client, profile_dict, monkeypatch, tmp_path):
    run, _ = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    assert client.get(f"/api/v1/runs/{run.run_id}/artifacts/report.md").status_code == 401


def test_tampered_artifact_is_refused(client, profile_dict, monkeypatch, tmp_path):
    run, token = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    run.artifacts["report.md"].write_bytes(b"tampered on disk")
    r = client.get(f"/api/v1/runs/{run.run_id}/artifacts/report.md",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409


# ------------------------------------------------------------------ publish
def test_publish_without_dnsimple_is_not_configured(client, profile_dict, monkeypatch, tmp_path):
    monkeypatch.delenv("DNSIMPLE_API_TOKEN", raising=False)
    run, token = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    r = client.post(f"/api/v1/runs/{run.run_id}/publish",
                    json={"environment": "sandbox", "publish_consent": True},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_configured"      # never a fake sandbox_record_created
    assert body["record_id"] is None and body["public_url"] is None
    assert "local-only" in body["fallback_url"]


def test_publish_requires_consent(client, profile_dict, monkeypatch, tmp_path):
    run, token = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    r = client.post(f"/api/v1/runs/{run.run_id}/publish",
                    json={"environment": "sandbox", "publish_consent": False},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


def test_production_publish_blocked(client, profile_dict, monkeypatch, tmp_path):
    run, token = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    r = client.post(f"/api/v1/runs/{run.run_id}/publish",
                    json={"environment": "production", "publish_consent": True},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "PUBLISH_APPROVAL_REQUIRED"


def test_dnsimple_adapter_refuses_url_target(monkeypatch):
    from providers import dnsimple
    from providers.errors import ProviderError
    monkeypatch.setenv("DNSIMPLE_API_TOKEN", "stub-token")
    monkeypatch.setenv("DNSIMPLE_ACCOUNT_ID", "1")
    with pytest.raises(ProviderError) as exc:
        dnsimple.create_cname("tp", "https://example.com/path")
    assert exc.value.code == "EVIDENCE_INVALID"


def test_dnsimple_adapter_creates_and_reads_back_with_stub(monkeypatch):
    import httpx
    from providers import dnsimple
    monkeypatch.setenv("DNSIMPLE_API_TOKEN", "stub-token")
    monkeypatch.setenv("DNSIMPLE_ACCOUNT_ID", "1")
    monkeypatch.setenv("DNSIMPLE_ZONE", "example.test")
    monkeypatch.setenv("DNSIMPLE_BASE_URL", "https://api.sandbox.dnsimple.test/v2")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "GET" and request.url.path.endswith("/records"):
            return httpx.Response(200, json={"data": []})
        if request.method == "POST":
            return httpx.Response(201, json={"data": {"id": 4242}})
        return httpx.Response(200, json={"data": {"id": 4242, "content": "target.example.test"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        out = dnsimple.create_cname("tp-run", "target.example.test", client=c)
    assert out["record_id"] == "4242" and out["created"] is True
    assert any(m == "POST" for m, _ in calls)
    assert calls[-1][0] == "GET"  # readback happened


def test_dnsimple_conflicting_record_is_an_error(monkeypatch):
    import httpx
    from providers import dnsimple
    from providers.errors import ProviderError
    monkeypatch.setenv("DNSIMPLE_API_TOKEN", "stub-token")
    monkeypatch.setenv("DNSIMPLE_ACCOUNT_ID", "1")
    monkeypatch.setenv("DNSIMPLE_ZONE", "example.test")

    def handler(request):
        return httpx.Response(200, json={"data": [{"id": 9, "content": "other.example.test"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        with pytest.raises(ProviderError) as exc:
            dnsimple.create_cname("tp-run", "target.example.test", client=c)
    assert exc.value.code == "EVIDENCE_INVALID"


# ------------------------------------------------------------- public report
def test_public_report_404_without_publish(client):
    assert client.get("/p/never-published-token").status_code == 404


def test_public_report_is_sanitized(client, profile_dict, monkeypatch, tmp_path, follower_case):
    import analyzer
    from app.models import Followers
    run, token = _queued(client, profile_dict, monkeypatch)
    _finish(run, tmp_path)
    run.result.followers = Followers.model_validate(analyzer.analyze(follower_case))
    run.result.actions[0].title = '<script>alert("xss")</script>'
    client.post(f"/api/v1/runs/{run.run_id}/publish",
                json={"environment": "sandbox", "publish_consent": True},
                headers={"Authorization": f"Bearer {token}"})
    html = client.get(f"/p/{run.public_token}").text
    assert "<script>alert" not in html and "&lt;script&gt;" in html
    for handle in ("tp_retained_a", "tp_old_name", "tp_missing", "tp_new_name"):
        assert handle not in html          # no follower identifiers
    assert token not in html                # no bearer token
    assert "old_count" in html              # aggregates are allowed


def test_public_html_escapes_model_text():
    from app.models import Result
    from tests.test_actions import PROFILE, good
    from app.pipeline import _validate_actions
    from providers.youtube import synthetic_sources
    sources = synthetic_sources("q")
    raw = good()
    raw[0]["production_package"]["publishing_package"]["title"] = "<img src=x onerror=alert(1)>"
    actions = _validate_actions(raw, PROFILE, {s["id"] for s in sources})
    result = Result(evidence_mode="synthetic", sample_notice=None, sources=sources,
                    opportunities=[], followers=None, actions=actions, limitations=[], artifacts=[])
    html = render_public_html(result)
    assert "<img" not in html        # the tag is inert after escaping
    assert "&lt;img" in html


# ------------------------------------------- provider failure -> honest state
def test_provider_failure_ends_failed_not_fake_success(profile_dict, monkeypatch):
    from providers.errors import ProviderError
    from app import pipeline
    from app.store import RunState
    monkeypatch.setattr(pipeline.nosana, "_client",
                        lambda: (_ for _ in ()).throw(
                            ProviderError("PROVIDER_UNAVAILABLE", "stubbed outage", True)))
    run = RunState("run_stub_fail", "fp")
    worker.execute(run, Profile.model_validate(profile_dict), None)
    assert run.status == "failed"
    assert run.result is None
    assert run.error["code"] == "PROVIDER_UNAVAILABLE"
    assert "stubbed outage" in run.error["message"]


def test_ai_output_invalid_after_one_repair_is_partial(profile_dict, monkeypatch):
    from app import pipeline
    from app.store import RunState

    class FakeSandbox:
        sandbox_id = "sbx-stub"

        def start(self): return self.sandbox_id
        def exec(self, *a, **k): return 0, ""
        def upload(self, *a, **k): return None
        def download(self, *a, **k): raise AssertionError("not reached")
        def stop(self): return "deleted"

    monkeypatch.setattr(pipeline.nosana, "_client", lambda: object())
    monkeypatch.setattr(pipeline.nosana, "pick_model", lambda c=None: "stub/model")
    monkeypatch.setattr(worker.nosana, "_client", lambda: object())
    monkeypatch.setattr(worker.nosana, "pick_model", lambda c=None: "stub/model")
    monkeypatch.setattr(worker.daytona_sandbox, "DaytonaRun", FakeSandbox)
    monkeypatch.setattr(pipeline, "stage_analyze", lambda run, sb, fi: None)
    calls = {"n": 0}

    def fake_complete(system, user, model=None, client=None, max_tokens=0):
        calls["n"] += 1
        receipt = {"model": "stub/model", "remote_id": "id-%d" % calls["n"],
                   "duration_ms": 1, "usage": {"total_tokens": 1}}
        if calls["n"] == 1:
            return {"weaknesses": ["w"]}, receipt, "{}"
        return {"actions": []}, receipt, "{}"   # always invalid

    monkeypatch.setattr(pipeline.nosana, "complete_json", fake_complete)
    run = RunState("run_stub_invalid", "fp")
    worker.execute(run, Profile.model_validate(profile_dict), None)
    assert run.status == "partial"
    assert run.error["code"] == "AI_OUTPUT_INVALID"
    assert calls["n"] == 3      # plan + recommend + exactly one repair


# ------------------------------------------------------- optional live test
@pytest.mark.skipif(os.environ.get("TRENDPILOT_LIVE_TEST") != "1",
                    reason="set TRENDPILOT_LIVE_TEST=1 to hit real Nosana/Daytona")
def test_live_nosana_model_listing():
    from providers import nosana
    model = nosana.pick_model()
    assert isinstance(model, str) and model
