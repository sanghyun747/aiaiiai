"""Pydantic models mirroring contracts/v1.openapi.json (contract 1.1.0).

snake_case field names, RFC3339 with offset for times, null = unknown.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .config import CONTRACT_VERSION


class Profile(BaseModel):
    model_config = {"extra": "forbid"}
    niche: str = Field(min_length=1, max_length=200)
    audience: str = Field(min_length=1, max_length=200)
    goal: Literal["views", "followers", "leads"]
    format: Literal["instagram_reel", "youtube_short"]
    weekly_minutes: int = Field(ge=10, le=2000)
    query: str = Field(min_length=1, max_length=200)
    data_mode: Literal["demo", "live"]
    sample_followers: bool
    pair_is_consecutive: bool
    cloud_processing_consent: bool


class Health(BaseModel):
    contract_version: str = CONTRACT_VERSION
    ok: bool
    configured: dict


class Accepted(BaseModel):
    contract_version: str = CONTRACT_VERSION
    run_id: str
    access_token: str
    status: Literal["queued"] = "queued"


class Error(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorEnvelope(BaseModel):
    contract_version: str = CONTRACT_VERSION
    error: Error


class Trace(BaseModel):
    provider: Literal["nosana", "daytona", "dnsimple", "youtube"]
    operation: str
    mode: Literal["live", "mock", "cached"]
    status: Literal["success", "failed", "skipped"]
    remote_id: Optional[str] = None
    executed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    artifact_sha256: Optional[str] = None
    detail: str = ""


class Source(BaseModel):
    id: str
    platform: Literal["youtube", "instagram", "manual", "synthetic"]
    source_mode: Literal["live", "cached", "synthetic", "manual"]
    url: Optional[str] = None
    title: str
    published_at: Optional[str] = None
    observed_at: str
    views: Optional[int] = None
    note: str = ""


class Opportunity(BaseModel):
    id: str
    title: str
    source_ids: List[str]
    reason: str
    mean_views_per_hour: Optional[float] = None
    momentum_evidence: Literal[
        "single_observation", "measured_growth", "measured_acceleration", "insufficient"
    ]


class Audit(BaseModel):
    old_username: str
    new_username: Optional[str] = None
    status: Literal[
        "confirmed_rename_still_current_follower",
        "confirmed_rename_relationship_absent",
        "checked_no_confirmed_rename",
        "username_change_not_ruled_out",
    ]
    method: Literal["export_continuity", "public_manual", "stable_account_id", "unresolved", "synthetic_fixture"]
    checked_at: str
    access_context: Literal["offline_exports", "non_login_public", "synthetic_fixture"]
    evidence: List[str] = []
    active_evidence: List[str] = []
    relationship_absent: bool = False


class Followers(BaseModel):
    input_kind: Literal["synthetic", "user_upload"]
    old_count: int
    current_count: int
    export_count_delta: int
    retained_count: int
    raw_missing_count: int
    raw_new_count: int
    outside_window_count: int
    renamed_still_following_count: int
    relationship_absent_count: int
    unresolved_count: int
    explicitly_inactive_count: int
    new_observed_excluding_renames: int
    audits: List[Audit]
    scope_note: str


class ScriptPackage(BaseModel):
    model_config = {"extra": "forbid"}
    hook: str = Field(min_length=1)
    intro: str = Field(min_length=1)
    body: List[str] = Field(min_length=1)
    ending: str = Field(min_length=1)
    cta: str = Field(min_length=1)


class Shot(BaseModel):
    model_config = {"extra": "forbid"}
    order: int = Field(ge=1)
    duration_sec: int = Field(ge=1, le=120)
    visual: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)


class EditingPlan(BaseModel):
    model_config = {"extra": "forbid"}
    pace: str = Field(min_length=1)
    caption_style: str = Field(min_length=1)
    cut_plan: str = Field(min_length=1)
    music_direction: str = Field(min_length=1)
    b_roll_notes: List[str] = Field(min_length=1)


class ThumbnailPlan(BaseModel):
    model_config = {"extra": "forbid"}
    concept: str = Field(min_length=1)
    text: str = Field(min_length=1)
    composition: str = Field(min_length=1)
    generation_prompt: str = Field(min_length=1)


class PublishingPackage(BaseModel):
    model_config = {"extra": "forbid"}
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    hashtags: List[str] = Field(min_length=1)
    cta: str = Field(min_length=1)
    target_metric: str = Field(min_length=1)
    posting_notes: str = Field(min_length=1)


class ProductionPackage(BaseModel):
    model_config = {"extra": "forbid"}
    script: ScriptPackage
    shot_list: List[Shot] = Field(min_length=1)
    editing_plan: EditingPlan
    thumbnail_plan: ThumbnailPlan
    publishing_package: PublishingPackage


class Action(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    strategy_mode: Literal["safe_bet", "growth_experiment"]
    weakness_target: Optional[str] = None
    title: str = Field(min_length=1)
    source_ids: List[str] = Field(min_length=1)
    fit_reason: str = Field(min_length=1)
    hook_a: str = Field(min_length=1)
    hook_b: str = Field(min_length=1)
    outline: List[str] = Field(min_length=1)
    caption: str = Field(min_length=1)
    production_minutes: int = Field(ge=1, le=2000)
    cta: str = Field(min_length=1)
    monetization_hypothesis: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    baseline: Optional[float] = None
    measurement_window_hours: int = Field(ge=1)
    success_rule: str = Field(min_length=1)
    production_package: ProductionPackage


class Artifact(BaseModel):
    name: Literal[
        "report.md", "content-strategy.json", "script.md", "shot-list.json",
        "editing-guide.md", "thumbnail-plan.md", "publishing-package.md",
    ]
    path: str
    sha256: str


class Result(BaseModel):
    evidence_mode: Literal["live", "cached", "synthetic", "mixed"]
    sample_notice: Optional[str] = None
    sources: List[Source]
    opportunities: List[Opportunity]
    followers: Optional[Followers] = None
    actions: List[Action]
    limitations: List[str]
    artifacts: List[Artifact]


class Run(BaseModel):
    contract_version: str = CONTRACT_VERSION
    run_id: str
    status: Literal["queued", "running", "succeeded", "partial", "failed"]
    stage: Literal["validate", "plan", "analyze", "recommend", "render", "done"]
    is_mock: bool
    created_at: str
    updated_at: str
    trace: List[Trace] = []
    result: Optional[Result] = None
    error: Optional[Error] = None


class PublishRequest(BaseModel):
    model_config = {"extra": "forbid"}
    environment: Literal["sandbox", "production"]
    publish_consent: bool


class Publication(BaseModel):
    environment: Literal["sandbox", "production"]
    status: Literal["sandbox_record_created", "dns_pending", "published", "not_configured", "failed"]
    record_id: Optional[str] = None
    public_url: Optional[str] = None
    fallback_url: Optional[str] = None
    note: str = ""
