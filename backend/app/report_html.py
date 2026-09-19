"""Sanitized public HTML. Allowlisted aggregates only, everything escaped.

No follower usernames, no private audit rows, no tokens, no provider secrets,
no model-supplied HTML or raw markdown HTML is rendered.
"""
from __future__ import annotations

from html import escape


def render_public_html(result) -> str:
    label = {"safe_bet": "SAFE BET", "growth_experiment": "GROWTH EXPERIMENT"}
    p = ["<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">",
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
         "<meta name=\"robots\" content=\"noindex,nofollow\">",
         "<title>TrendPilot 공개 리포트</title>",
         "<style>body{font-family:system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;",
         "line-height:1.6;color:#1a1a1a;background:#fff}h2{margin-top:2rem}li{margin:.25rem 0}",
         "@media(prefers-color-scheme:dark){body{background:#141414;color:#eee}}</style></head><body>",
         "<h1>TrendPilot 공개 리포트</h1>",
         f"<p>증거 모드: {escape(result.evidence_mode)}</p>"]
    if result.sample_notice:
        p.append(f"<p><strong>{escape(result.sample_notice)}</strong></p>")
    p.append("<p>촬영을 제외한 제작 핸드오프입니다. 완성된 영상이 편집·렌더링되지 않았습니다.</p>")
    p.append("<h2>참고 근거</h2><ul>")
    for s in result.sources:
        link = (f' — <a href="{escape(s.url)}" rel="noopener noreferrer" target="_blank">출처</a>'
                if s.url and s.url.startswith("https://") else " — (URL 없음)")
        p.append(f"<li>[{escape(s.source_mode)}] {escape(s.title)} — 관측 {escape(s.observed_at)}{link}</li>")
    p.append("</ul>")
    if result.followers:
        f = result.followers
        p.append("<h2>팔로워 집계</h2><ul>")
        for k in ("old_count", "current_count", "export_count_delta", "retained_count",
                  "raw_missing_count", "raw_new_count", "unresolved_count",
                  "renamed_still_following_count", "new_observed_excluding_renames"):
            p.append(f"<li>{escape(k)}: {escape(str(getattr(f, k)))}</li>")
        p.append("</ul>")
        p.append(f"<p>{escape(f.scope_note)}</p>")
        p.append("<p>개별 계정 식별자와 감사 기록은 공개 리포트에 포함하지 않습니다.</p>")
    p.append("<h2>실행 액션</h2>")
    for a in result.actions:
        pp = a.production_package
        p.append(f"<h3>[{escape(label.get(a.strategy_mode, a.strategy_mode))}] {escape(a.title)}</h3><ul>")
        p.append(f"<li>약점 타깃: {escape(a.weakness_target or '없음')}</li>")
        p.append(f"<li>제작 시간: {escape(str(a.production_minutes))}분</li>")
        p.append(f"<li>지표: {escape(a.metric)}</li>")
        p.append(f"<li>성공 판정: {escape(a.success_rule)}</li>")
        p.append(f"<li>훅: {escape(pp.script.hook)}</li>")
        p.append(f"<li>게시 제목(가설): {escape(pp.publishing_package.title)}</li>")
        p.append(f"<li>해시태그(가설): {escape(' '.join(pp.publishing_package.hashtags))}</li>")
        p.append("</ul>")
    p.append("<h2>한계</h2><ul>")
    for lim in result.limitations:
        p.append(f"<li>{escape(lim)}</li>")
    p.append("</ul></body></html>")
    return "".join(p)
