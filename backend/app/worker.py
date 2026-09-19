"""Bounded worker: at most MAX_CONCURRENT_JOBS jobs in one backend process."""
from __future__ import annotations

import json
import secrets
import traceback
from concurrent.futures import ThreadPoolExecutor

from . import pipeline
from .config import CONTRACT_VERSION, MAX_CONCURRENT_JOBS, live_providers_enabled
from .models import Followers, Result
from providers import daytona_sandbox, nosana
from providers.errors import ProviderError

EXECUTOR = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS, thread_name_prefix="tp-job")

BASE_LIMITATIONS = [
    "단일 관측 기반 기술 통계입니다. 성장 속도·가속·인스타그램 유행 순위가 아닙니다.",
    "제목·해시태그·썸네일 문구는 검증할 가설이며 도달을 보장하지 않습니다.",
    "편집 가이드 문서만 생성했습니다. 실제 영상 편집이나 렌더링은 수행하지 않았습니다.",
    "이름 변경 후보는 export 연속성 일치이며 계정 동일성 증명이 아닙니다. 미해소 항목은 손실이 아닙니다.",
    "언팔로우 원인은 판단하지 않습니다.",
    "기준값(baseline)이 없으면 먼저 같은 조건의 비교 기준을 직접 수집해야 합니다.",
]


def _finish_error(run, code, message, retryable, status):
    run.status = status
    run.stage = "done"
    run.error = {"code": code, "message": message, "retryable": retryable}
    run.touch()


def execute(run, profile, uploads):
    sandbox = None
    try:
        follower_input = pipeline.stage_validate(run, profile, uploads)

        if not live_providers_enabled():
            raise pipeline.StageFailure(
                "PROVIDER_UNAVAILABLE", "Live providers are disabled for this process.", False)

        sources, evidence_mode = pipeline.collect_sources(run, profile)
        opportunities = pipeline.build_opportunities(sources)

        client = nosana._client()
        model = nosana.pick_model(client)

        # Daytona sandbox spans analyze + render.
        sandbox = daytona_sandbox.DaytonaRun()
        sandbox.start()
        run.sandbox_id = sandbox.sandbox_id
        sandbox.exec("mkdir -p /tmp/tp/out", timeout=60)

        followers = pipeline.stage_analyze(run, sandbox, follower_input)

        plan = pipeline.stage_plan(run, profile, sources, opportunities, followers, client, model)
        actions = pipeline.stage_recommend(run, profile, sources, opportunities,
                                           followers, plan, client, model)

        payload = {
            "contract_version": CONTRACT_VERSION,
            "evidence_mode": evidence_mode,
            "profile": profile.model_dump(),
            "sources": sources,
            "opportunities": opportunities,
            "followers": followers,
            "actions": [a.model_dump() for a in actions],
            "limitations": BASE_LIMITATIONS,
        }
        artifacts = pipeline.stage_render(run, sandbox, payload)

        rundir = pipeline.RUNTIME_DIR / run.run_id / "artifacts"
        run.artifacts = {a["name"]: rundir / a["name"] for a in artifacts}

        result = Result(
            evidence_mode=evidence_mode,
            sample_notice=("합성 입력과 합성 참고 근거를 사용했습니다. 실제 SNS 유행이나 실제 계정 결과가 아닙니다. "
                           "Nosana 추론과 Daytona 샌드박스 실행은 실제로 수행되었습니다.")
            if evidence_mode == "synthetic" else None,
            sources=sources, opportunities=opportunities,
            followers=Followers.model_validate(followers) if followers else None,
            actions=actions, limitations=BASE_LIMITATIONS, artifacts=artifacts,
        )
        run.result = result
        has_report = any(a["name"] == "report.md" for a in artifacts)
        run.status = "succeeded" if (len(actions) == 3 and has_report) else "partial"
        run.stage = "done"
        if run.status == "partial":
            run.error = {"code": "ARTIFACT_NOT_READY",
                         "message": "리포트 산출물 검증이 완료되지 않아 partial로 종료했습니다.",
                         "retryable": True}
        run.touch()
    except pipeline.StageFailure as exc:
        _finish_error(run, exc.code, exc.message, exc.retryable, "partial" if exc.partial else "failed")
    except ProviderError as exc:
        _finish_error(run, exc.code, exc.message, exc.retryable, "failed")
    except Exception as exc:  # no stack traces leak to clients
        _finish_error(run, "PROVIDER_UNAVAILABLE",
                      f"{type(exc).__name__}: {str(exc)[:300]}", False, "failed")
    finally:
        if sandbox is not None:
            state = sandbox.stop()
            run.add_trace({"provider": "daytona", "operation": "sandbox_stop", "mode": "live",
                           "status": "success" if state == "deleted" else "failed",
                           "remote_id": sandbox.sandbox_id, "executed_at": pipeline.now(),
                           "duration_ms": None, "artifact_sha256": None,
                           "detail": f"sandbox {state}"})


def submit(run, profile, uploads):
    EXECUTOR.submit(execute, run, profile, uploads)
