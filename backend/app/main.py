"""TrendPilot backend — frozen contract 1.1.0. 127.0.0.1:8317."""
from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path

from fastapi import FastAPI, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

from . import exports, worker
from .config import ARTIFACT_NAMES, CONTRACT_VERSION, MAX_UPLOAD_BYTES, RUNTIME_DIR, configured
from .models import (Accepted, Error, ErrorEnvelope, Health, Profile, PublishRequest,
                     Publication, Run)
from .report_html import render_public_html
from .store import STORE
from providers import dnsimple
from providers.errors import ProviderError

app = FastAPI(title="TrendPilot backend", version=CONTRACT_VERSION, docs_url=None, redoc_url=None)

# Exactly the approved frontend origin. Never wildcard with credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5317", "http://localhost:5317"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Idempotency-Key", "Content-Type"],
)

STATUS_FOR_CODE = {
    "INVALID_PROFILE": 422, "INVALID_ZIP": 400, "ZIP_LIMIT_EXCEEDED": 413,
    "UNSUPPORTED_EXPORT": 415, "INCOMPLETE_EXPORT_PAIR": 422, "CONSENT_REQUIRED": 422,
    "IDEMPOTENCY_CONFLICT": 409, "NOT_FOUND": 404, "UNAUTHORIZED": 401, "JOB_LIMIT": 429,
    "PROVIDER_UNAVAILABLE": 503, "MODEL_UNAVAILABLE": 503, "AI_OUTPUT_INVALID": 503,
    "EVIDENCE_INVALID": 422, "ARTIFACT_NOT_READY": 409,
    "PUBLISH_APPROVAL_REQUIRED": 422, "DNS_NOT_CONFIGURED": 503,
}


def fail(code: str, message: str, retryable: bool = False):
    """Structured error. Never exposes stacks, tokens, paths or private rows."""
    envelope = ErrorEnvelope(error=Error(code=code, message=message, retryable=retryable))
    return HTTPException(status_code=STATUS_FOR_CODE.get(code, 400),
                         detail=envelope.model_dump())


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content=ErrorEnvelope(
        error=Error(code="NOT_FOUND" if exc.status_code == 404 else "INVALID_PROFILE",
                    message=str(detail), retryable=False)).model_dump())


def _authorize(run_id: str, authorization: str | None):
    run = STORE.get(run_id)
    if run is None:
        raise fail("NOT_FOUND", "Unknown run.")
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token or not secrets.compare_digest(token, run.access_token):
        raise fail("UNAUTHORIZED", "A valid per-run bearer token is required.")
    return run


def _run_model(run) -> Run:
    return Run(run_id=run.run_id, status=run.status, stage=run.stage, is_mock=run.is_mock,
               created_at=run.created_at, updated_at=run.updated_at, trace=run.trace,
               result=run.result, error=run.error)


@app.get("/api/v1/health", response_model=Health)
def health():
    # configured = key presence only, NOT a successful remote call.
    return Health(ok=True, configured=configured())


@app.post("/api/v1/runs", status_code=202, response_model=Accepted)
async def create_run(
    profile_json: str = Form(...),
    old_export: UploadFile | None = None,
    current_export: UploadFile | None = None,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    if not idempotency_key or len(idempotency_key) < 8:
        raise fail("INVALID_PROFILE", "A fresh random Idempotency-Key header is required.")
    try:
        raw = json.loads(profile_json)
        profile = Profile.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise fail("INVALID_PROFILE", f"profile_json failed schema validation: {str(exc)[:200]}")

    has_old, has_cur = old_export is not None, current_export is not None
    if profile.sample_followers and (has_old or has_cur):
        raise fail("INVALID_PROFILE",
                   "sample_followers=true generates synthetic exports and rejects uploaded files.")
    if has_old != has_cur:
        raise fail("INCOMPLETE_EXPORT_PAIR",
                   "Both old_export and current_export are required; a single export never proves losses.")
    if has_old and not profile.cloud_processing_consent:
        raise fail("CONSENT_REQUIRED",
                   "Uploading real exports requires cloud_processing_consent=true after the disclosure.")

    # Fingerprint binds the idempotency key to the payload. The key itself is never logged.
    hasher = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    uploads = None
    if has_old:
        if STORE.active_count() >= 2:
            raise fail("JOB_LIMIT", "Too many concurrent jobs; retry shortly.", True)
        tmp = RUNTIME_DIR / "uploads" / secrets.token_hex(8)
        tmp.mkdir(parents=True, exist_ok=True)
        uploads = {}
        for key, upload in (("old", old_export), ("current", current_export)):
            data = await upload.read()
            if len(data) > MAX_UPLOAD_BYTES:
                raise fail("ZIP_LIMIT_EXCEEDED", "Uploaded export exceeds the size limit.")
            hasher.update(hashlib.sha256(data).digest())
            path = tmp / f"{key}.zip"
            path.write_bytes(data)
            uploads[key] = path
        for path in uploads.values():
            try:
                exports.parse_export(path)
            except exports.ExportError as exc:
                raise fail(exc.code, exc.message)

    try:
        run, reused = STORE.create(idempotency_key, hasher.hexdigest())
    except KeyError:
        raise fail("IDEMPOTENCY_CONFLICT",
                   "This Idempotency-Key was already used with a different payload.")
    if reused:
        return Accepted(run_id=run.run_id, access_token=run.access_token, status="queued")
    if STORE.active_count() > 2:
        raise fail("JOB_LIMIT", "Too many concurrent jobs; retry shortly.", True)
    worker.submit(run, profile, uploads)
    return Accepted(run_id=run.run_id, access_token=run.access_token, status="queued")


@app.get("/api/v1/runs/{run_id}", response_model=Run)
def get_run(run_id: str, authorization: str | None = Header(None)):
    return _run_model(_authorize(run_id, authorization))


def _artifact_response(run, name: str):
    path: Path | None = run.artifacts.get(name)  # per-run allowlist, not a filesystem path
    if name not in ARTIFACT_NAMES or path is None or not path.exists():
        raise fail("NOT_FOUND", "Artifact is not available for this run.")
    data = path.read_bytes()
    listed = next((a for a in (run.result.artifacts if run.result else []) if a.name == name), None)
    if listed and hashlib.sha256(data).hexdigest() != listed.sha256:
        raise fail("ARTIFACT_NOT_READY", "Artifact hash no longer matches the verified value.")
    media = "application/json" if name.endswith(".json") else "text/markdown; charset=utf-8"
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{name}"',
        "X-Content-Type-Options": "nosniff",
    })


@app.get("/api/v1/runs/{run_id}/artifacts/report.md")
def get_report(run_id: str, authorization: str | None = Header(None)):
    return _artifact_response(_authorize(run_id, authorization), "report.md")


@app.get("/api/v1/runs/{run_id}/artifacts/{artifact_name}")
def get_artifact(run_id: str, artifact_name: str, authorization: str | None = Header(None)):
    return _artifact_response(_authorize(run_id, authorization), artifact_name)


@app.post("/api/v1/runs/{run_id}/publish", response_model=Publication)
def publish(run_id: str, body: PublishRequest, authorization: str | None = Header(None)):
    run = _authorize(run_id, authorization)
    if body.publish_consent is not True:
        raise fail("PUBLISH_APPROVAL_REQUIRED", "Explicit publish_consent=true is required.")
    if run.result is None:
        raise fail("ARTIFACT_NOT_READY", "This run has no result to publish.")
    if body.environment == "production":
        raise fail("PUBLISH_APPROVAL_REQUIRED",
                   "Production publishing stays disabled until DNS resolution, TLS and the "
                   "report route are separately verified and approved.")
    if run.public_token is None:
        run.public_token = secrets.token_urlsafe(24)
        STORE.register_public(run.public_token, run.run_id)
    fallback = f"http://127.0.0.1:8317/p/{run.public_token} (local-only)"
    if not dnsimple.is_configured():
        pub = Publication(environment="sandbox", status="not_configured", record_id=None,
                          public_url=None, fallback_url=fallback,
                          note="DNSimple 토큰이 이 머신에 없습니다. DNS 레코드를 만들지 않았습니다. "
                               "비공개 리포트 다운로드는 그대로 동작합니다.")
        run.add_trace({"provider": "dnsimple", "operation": "publish", "mode": "live",
                       "status": "failed", "remote_id": None, "executed_at": run.updated_at,
                       "duration_ms": None, "artifact_sha256": None,
                       "detail": "DNS_NOT_CONFIGURED: 자격증명 없음. sandbox_record_created 아님."})
        run.publication = pub
        return pub
    try:
        created = dnsimple.create_cname(f"tp-{run.run_id}", "trendpilot-report.invalid-host")
    except ProviderError as exc:
        run.add_trace({"provider": "dnsimple", "operation": "publish", "mode": "live",
                       "status": "failed", "remote_id": None, "executed_at": run.updated_at,
                       "duration_ms": None, "artifact_sha256": None, "detail": exc.message})
        return Publication(environment="sandbox", status="failed", record_id=None, public_url=None,
                           fallback_url=fallback, note=exc.message)
    run.add_trace({"provider": "dnsimple", "operation": "publish", "mode": "live",
                   "status": "success", "remote_id": created["record_id"],
                   "executed_at": run.updated_at, "duration_ms": None, "artifact_sha256": None,
                   "detail": "Sandbox CNAME created and read back."})
    return Publication(environment="sandbox", status="sandbox_record_created",
                       record_id=created["record_id"], public_url=None, fallback_url=fallback,
                       note="샌드박스 레코드 생성 및 재조회 완료. 공개 게시가 아닙니다.")


@app.get("/p/{public_token}", response_class=HTMLResponse)
def public_report(public_token: str):
    run = STORE.by_public(public_token)
    if run is None or run.result is None:
        raise HTTPException(status_code=404, detail="Not found")
    return HTMLResponse(content=render_public_html(run.result), headers={
        "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    })
