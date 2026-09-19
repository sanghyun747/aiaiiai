"""Runs INSIDE the Daytona sandbox. Stdlib only, no network.

Deterministic rendering of the validated production packages into the seven
contract artifacts using fixed templates. The LLM never writes these files;
it only supplied validated JSON fields that are escaped into fixed structure.
"""
import hashlib
import json
import os
import sys


def esc(v):
    if v is None:
        return "(없음)"
    return str(v).replace("\r", " ").replace("\n", " ").strip()


def bullets(items):
    return "\n".join("- " + esc(i) for i in (items or [])) or "- (없음)"


def render(payload, outdir):
    os.makedirs(outdir, exist_ok=True)
    actions = payload["actions"]
    followers = payload.get("followers")
    sources = payload.get("sources", [])
    opportunities = payload.get("opportunities", [])
    profile = payload.get("profile", {})
    limitations = payload.get("limitations", [])
    label = {"safe_bet": "SAFE BET", "growth_experiment": "GROWTH EXPERIMENT"}

    # ---------- report.md ----------
    L = ["# TrendPilot 실행 리포트", "",
         "- 증거 모드: %s" % esc(payload.get("evidence_mode")),
         "- 니치: %s / 대상: %s" % (esc(profile.get("niche")), esc(profile.get("audience"))),
         "- 주간 가용 시간: %s분" % esc(profile.get("weekly_minutes")),
         "- 총 제작 시간 합계: %d분" % sum(a["production_minutes"] for a in actions),
         "",
         "이 리포트는 촬영을 제외한 제작 핸드오프입니다. 완성된 영상이 편집·렌더링되지 않았습니다.",
         "", "## 참고 근거", ""]
    for s in sources:
        L.append("- [%s] %s — 관측 %s, 조회수 %s%s" % (
            esc(s["source_mode"]), esc(s["title"]), esc(s["observed_at"]),
            esc(s.get("views")), (" — " + esc(s["url"])) if s.get("url") else " — (URL 없음)"))
    L += ["", "## 기회 가설", ""]
    for o in opportunities:
        L.append("- %s (근거 ID: %s, 근거 강도: %s)" % (
            esc(o["title"]), ", ".join(esc(x) for x in o["source_ids"]), esc(o["momentum_evidence"])))
    if followers:
        L += ["", "## 팔로워 집계 (집계값만)", "",
              "| 항목 | 값 |", "| --- | --- |"]
        for k in ("input_kind", "old_count", "current_count", "export_count_delta", "retained_count",
                  "raw_missing_count", "raw_new_count", "outside_window_count",
                  "renamed_still_following_count", "relationship_absent_count", "unresolved_count",
                  "explicitly_inactive_count", "new_observed_excluding_renames"):
            L.append("| %s | %s |" % (k, esc(followers[k])))
        L += ["", esc(followers.get("scope_note")),
              "", "미해소 항목은 손실이 아닙니다. 언팔로우 원인은 판단하지 않습니다."]
    L += ["", "## 실행 액션 3개", ""]
    for a in actions:
        pp = a["production_package"]
        L += ["### [%s] %s" % (label.get(a["strategy_mode"], esc(a["strategy_mode"])), esc(a["title"])), "",
              "- 약점 타깃: %s" % esc(a.get("weakness_target")),
              "- 근거 ID: %s" % ", ".join(esc(x) for x in a["source_ids"]),
              "- 적합 이유: %s" % esc(a["fit_reason"]),
              "- 제작 시간: %s분 / 지표: %s / 기준값: %s / 관측 %s시간" % (
                  esc(a["production_minutes"]), esc(a["metric"]),
                  esc(a.get("baseline")) if a.get("baseline") is not None else "없음(먼저 수집 필요)",
                  esc(a["measurement_window_hours"])),
              "- 성공 판정: %s" % esc(a["success_rule"]), "",
              "**1. 스크립트**", "", "- 훅: %s" % esc(pp["script"]["hook"]),
              "- 도입: %s" % esc(pp["script"]["intro"]), bullets(pp["script"]["body"]),
              "- 마무리: %s" % esc(pp["script"]["ending"]), "- CTA: %s" % esc(pp["script"]["cta"]), "",
              "**2. 샷 리스트**", "", "| # | 초 | 화면 | 나레이션 | 자막 |", "| --- | --- | --- | --- | --- |"]
        for sh in sorted(pp["shot_list"], key=lambda x: x["order"]):
            L.append("| %s | %s | %s | %s | %s |" % (
                esc(sh["order"]), esc(sh["duration_sec"]), esc(sh["visual"]),
                esc(sh["narration"]), esc(sh["subtitle"])))
        ed, th, pu = pp["editing_plan"], pp["thumbnail_plan"], pp["publishing_package"]
        L += ["", "**3. 편집 가이드(지침 문서이며 자동 편집 결과가 아님)**", "",
              "- 템포: %s" % esc(ed["pace"]), "- 자막 스타일: %s" % esc(ed["caption_style"]),
              "- 컷 구성: %s" % esc(ed["cut_plan"]),
              "- 음악 방향(설명만, 음원 미포함·라이선스 미보장): %s" % esc(ed["music_direction"]),
              bullets(ed["b_roll_notes"]), "",
              "**4. 썸네일 플랜**", "", "- 콘셉트: %s" % esc(th["concept"]),
              "- 텍스트: %s" % esc(th["text"]), "- 구도: %s" % esc(th["composition"]),
              "- 생성 프롬프트: %s" % esc(th["generation_prompt"]), "",
              "**5. 게시 패키지**", "", "- 제목: %s" % esc(pu["title"]),
              "- 설명: %s" % esc(pu["description"]),
              "- 해시태그(가설이며 도달 보장 아님): %s" % " ".join(esc(h) for h in pu["hashtags"]),
              "- CTA: %s" % esc(pu["cta"]), "- 목표 지표: %s" % esc(pu["target_metric"]),
              "- 게시 메모: %s" % esc(pu["posting_notes"]), ""]
    L += ["## 한계", "", bullets(limitations), ""]
    files = {"report.md": "\n".join(L)}

    # ---------- content-strategy.json ----------
    files["content-strategy.json"] = json.dumps({
        "contract_version": payload.get("contract_version"),
        "evidence_mode": payload.get("evidence_mode"),
        "profile": profile,
        "sources": sources,
        "opportunities": opportunities,
        "followers": followers,
        "actions": actions,
        "limitations": limitations,
    }, ensure_ascii=False, indent=2)

    # ---------- script.md ----------
    S = ["# 스크립트 모음", ""]
    for a in actions:
        sc = a["production_package"]["script"]
        S += ["## [%s] %s" % (label.get(a["strategy_mode"], ""), esc(a["title"])), "",
              "훅 A: %s" % esc(a["hook_a"]), "훅 B: %s" % esc(a["hook_b"]), "",
              "훅: %s" % esc(sc["hook"]), "도입: %s" % esc(sc["intro"]), "", bullets(sc["body"]),
              "", "마무리: %s" % esc(sc["ending"]), "CTA: %s" % esc(sc["cta"]), ""]
    files["script.md"] = "\n".join(S)

    # ---------- shot-list.json ----------
    files["shot-list.json"] = json.dumps([
        {"action_id": a["id"], "strategy_mode": a["strategy_mode"],
         "shots": sorted(a["production_package"]["shot_list"], key=lambda x: x["order"])}
        for a in actions], ensure_ascii=False, indent=2)

    # ---------- editing-guide.md ----------
    E = ["# 편집 가이드", "",
         "이 문서는 편집 지침입니다. 실제 영상 편집이나 렌더링은 수행되지 않았습니다.",
         "음악은 방향 설명만이며 음원 번들이나 라이선스를 제공하지 않습니다.", ""]
    for a in actions:
        ed = a["production_package"]["editing_plan"]
        E += ["## %s" % esc(a["title"]), "", "- 템포: %s" % esc(ed["pace"]),
              "- 자막 스타일: %s" % esc(ed["caption_style"]), "- 컷 구성: %s" % esc(ed["cut_plan"]),
              "- 음악 방향: %s" % esc(ed["music_direction"]), "- B롤:", bullets(ed["b_roll_notes"]), ""]
    files["editing-guide.md"] = "\n".join(E)

    # ---------- thumbnail-plan.md ----------
    T = ["# 썸네일 플랜", "", "생성 프롬프트는 시안 참고용이며 실제 이미지가 생성되지 않았습니다.", ""]
    for a in actions:
        th = a["production_package"]["thumbnail_plan"]
        T += ["## %s" % esc(a["title"]), "", "- 콘셉트: %s" % esc(th["concept"]),
              "- 텍스트: %s" % esc(th["text"]), "- 구도: %s" % esc(th["composition"]),
              "- 생성 프롬프트: %s" % esc(th["generation_prompt"]), ""]
    files["thumbnail-plan.md"] = "\n".join(T)

    # ---------- publishing-package.md ----------
    P = ["# 게시 패키지", "", "제목·해시태그·썸네일 문구는 검증할 가설이며 도달 보장이 아닙니다.", ""]
    for a in actions:
        pu = a["production_package"]["publishing_package"]
        P += ["## [%s] %s" % (label.get(a["strategy_mode"], ""), esc(a["title"])), "",
              "- 제목: %s" % esc(pu["title"]), "- 설명: %s" % esc(pu["description"]),
              "- 해시태그: %s" % " ".join(esc(h) for h in pu["hashtags"]), "- CTA: %s" % esc(pu["cta"]),
              "- 목표 지표: %s" % esc(pu["target_metric"]), "- 게시 메모: %s" % esc(pu["posting_notes"]), ""]
    files["publishing-package.md"] = "\n".join(P)

    manifest = []
    for name, text in files.items():
        data = text.encode("utf-8")
        with open(os.path.join(outdir, name), "wb") as fh:
            fh.write(data)
        manifest.append({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    return sorted(manifest, key=lambda m: m["name"])


if __name__ == "__main__":
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
    manifest = render(payload, sys.argv[2])
    with open(os.path.join(sys.argv[2], "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False)
    print(json.dumps(manifest, ensure_ascii=False))
