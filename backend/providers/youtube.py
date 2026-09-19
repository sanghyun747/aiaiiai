"""YouTube Data API adapter for bounded public reference evidence.

No API key is available on this machine, so runs fall back to synthetic
evidence with source_mode=synthetic, url=null and evidence_mode=synthetic.
Cached/synthetic evidence is never presented as live. Only deterministic
descriptive metrics are preserved; no acceleration or content analysis.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

from .errors import ProviderError

KST = timezone(timedelta(hours=9))
API = "https://www.googleapis.com/youtube/v3"


def is_configured() -> bool:
    return bool(os.environ.get("YOUTUBE_API_KEY"))


def now_rfc3339() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


def search_sources(query: str, limit: int = 3, client: httpx.Client = None) -> list:
    if not is_configured():
        raise ProviderError("PROVIDER_UNAVAILABLE", "YOUTUBE_API_KEY is not configured.", False)
    owns = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        key = os.environ["YOUTUBE_API_KEY"]
        s = client.get(API + "/search", params={
            "part": "snippet", "q": query, "type": "video", "maxResults": limit,
            "videoDuration": "short", "key": key,
        })
        if s.status_code >= 400:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"YouTube search failed: HTTP {s.status_code}", True)
        ids = [i["id"]["videoId"] for i in s.json().get("items", [])]
        if not ids:
            return []
        v = client.get(API + "/videos", params={
            "part": "snippet,statistics", "id": ",".join(ids), "key": key,
        })
        if v.status_code >= 400:
            raise ProviderError("PROVIDER_UNAVAILABLE", f"YouTube videos failed: HTTP {v.status_code}", True)
        observed = now_rfc3339()
        out = []
        for item in v.json().get("items", []):
            views = item.get("statistics", {}).get("viewCount")
            out.append({
                "id": "yt-" + item["id"],
                "platform": "youtube",
                "source_mode": "live",
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "title": item["snippet"]["title"][:200],
                "published_at": item["snippet"].get("publishedAt"),
                "observed_at": observed,
                "views": int(views) if views is not None else None,
                "note": "YouTube Data API 단일 관측값입니다. 성장 속도나 유행 순위가 아닙니다.",
            })
        return out
    finally:
        if owns:
            client.close()


def synthetic_sources(query: str) -> list:
    """Deterministic synthetic reference evidence. Never labelled live."""
    observed = now_rfc3339()
    base = datetime.now(KST).replace(microsecond=0)
    specs = [
        ("합성 예시: '%s' 루틴 소개" % query, 2400, 12),
        ("합성 예시: '%s' 체크리스트" % query, 3600, 24),
        ("합성 예시: '%s' 제작 과정" % query, 600, 6),
    ]
    out = []
    for i, (title, views, hours) in enumerate(specs, start=1):
        out.append({
            "id": f"syn-s{i}",
            "platform": "synthetic",
            "source_mode": "synthetic",
            "url": None,
            "title": title,
            "published_at": (base - timedelta(hours=hours)).isoformat(),
            "observed_at": observed,
            "views": views,
            "note": "합성 수치입니다. 실제 게시물·조회수·유행이 아닙니다.",
        })
    return out
