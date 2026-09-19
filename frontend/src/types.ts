export const CONTRACT_VERSION = '1.1.0' as const;

export type Goal = 'views' | 'followers' | 'leads';
export type ContentFormat = 'instagram_reel' | 'youtube_short';
export type DataMode = 'demo' | 'live';

export interface Profile {
  niche: string;
  audience: string;
  goal: Goal;
  format: ContentFormat;
  weekly_minutes: number;
  query: string;
  data_mode: DataMode;
  sample_followers: boolean;
  pair_is_consecutive: boolean;
  cloud_processing_consent: boolean;
}

export interface Health {
  contract_version: typeof CONTRACT_VERSION;
  ok: boolean;
  configured: {
    nosana: boolean;
    daytona: boolean;
    dnsimple: boolean;
    youtube: boolean;
  };
}

export interface Accepted {
  contract_version: typeof CONTRACT_VERSION;
  run_id: string;
  access_token: string;
  status: 'queued';
}

export interface ApiError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface ErrorEnvelope {
  contract_version: typeof CONTRACT_VERSION;
  error: ApiError;
}

export interface Trace {
  provider: 'nosana' | 'daytona' | 'dnsimple' | 'youtube';
  operation: string;
  mode: 'live' | 'mock' | 'cached';
  status: 'success' | 'failed' | 'skipped';
  remote_id: string | null;
  executed_at: string | null;
  duration_ms: number | null;
  artifact_sha256: string | null;
  detail: string;
}

export interface Source {
  id: string;
  platform: 'youtube' | 'instagram' | 'manual' | 'synthetic';
  source_mode: 'live' | 'cached' | 'synthetic' | 'manual';
  url: string | null;
  title: string;
  published_at: string | null;
  observed_at: string;
  views: number | null;
  note: string;
}

export interface Opportunity {
  id: string;
  title: string;
  source_ids: string[];
  reason: string;
  mean_views_per_hour: number | null;
  momentum_evidence:
    | 'single_observation'
    | 'measured_growth'
    | 'measured_acceleration'
    | 'insufficient';
}

export interface Audit {
  old_username: string;
  new_username: string | null;
  status:
    | 'confirmed_rename_still_current_follower'
    | 'confirmed_rename_relationship_absent'
    | 'checked_no_confirmed_rename'
    | 'username_change_not_ruled_out';
  method:
    | 'export_continuity'
    | 'public_manual'
    | 'stable_account_id'
    | 'unresolved'
    | 'synthetic_fixture';
  checked_at: string;
  access_context: 'offline_exports' | 'non_login_public' | 'synthetic_fixture';
  evidence: string[];
  active_evidence: string[];
  relationship_absent: boolean;
}

export interface Followers {
  input_kind: 'synthetic' | 'user_upload';
  old_count: number;
  current_count: number;
  export_count_delta: number;
  retained_count: number;
  raw_missing_count: number;
  raw_new_count: number;
  outside_window_count: number;
  renamed_still_following_count: number;
  relationship_absent_count: number;
  unresolved_count: number;
  explicitly_inactive_count: number;
  new_observed_excluding_renames: number;
  audits: Audit[];
  scope_note: string;
}

export interface ScriptPackage {
  hook: string;
  intro: string;
  body: string[];
  ending: string;
  cta: string;
}

export interface Shot {
  order: number;
  duration_sec: number;
  visual: string;
  narration: string;
  subtitle: string;
}

export interface EditingPlan {
  pace: string;
  caption_style: string;
  cut_plan: string;
  music_direction: string;
  b_roll_notes: string[];
}

export interface ThumbnailPlan {
  concept: string;
  text: string;
  composition: string;
  generation_prompt: string;
}

export interface PublishingPackage {
  title: string;
  description: string;
  hashtags: string[];
  cta: string;
  target_metric: string;
  posting_notes: string;
}

export interface ProductionPackage {
  script: ScriptPackage;
  shot_list: Shot[];
  editing_plan: EditingPlan;
  thumbnail_plan: ThumbnailPlan;
  publishing_package: PublishingPackage;
}

export interface Action {
  id: string;
  strategy_mode: 'safe_bet' | 'growth_experiment';
  weakness_target: string | null;
  title: string;
  source_ids: string[];
  fit_reason: string;
  hook_a: string;
  hook_b: string;
  outline: string[];
  caption: string;
  production_minutes: number;
  cta: string;
  monetization_hypothesis: string;
  metric: string;
  baseline: number | null;
  measurement_window_hours: number;
  success_rule: string;
  production_package: ProductionPackage;
}

export type ArtifactName =
  | 'report.md'
  | 'content-strategy.json'
  | 'script.md'
  | 'shot-list.json'
  | 'editing-guide.md'
  | 'thumbnail-plan.md'
  | 'publishing-package.md';

export interface Artifact {
  name: ArtifactName;
  path: string;
  sha256: string;
}

export interface Result {
  evidence_mode: 'live' | 'cached' | 'synthetic' | 'mixed';
  sample_notice: string | null;
  sources: Source[];
  opportunities: Opportunity[];
  followers: Followers | null;
  actions: Action[];
  limitations: string[];
  artifacts: Artifact[];
}

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'partial' | 'failed';
export type RunStage = 'validate' | 'plan' | 'analyze' | 'recommend' | 'render' | 'done';

export interface Run {
  contract_version: typeof CONTRACT_VERSION;
  run_id: string;
  status: RunStatus;
  stage: RunStage;
  is_mock: boolean;
  created_at: string;
  updated_at: string;
  trace: Trace[];
  result: Result | null;
  error: ApiError | null;
}

export interface PublishRequest {
  environment: 'sandbox' | 'production';
  publish_consent: true;
}

export interface Publication {
  environment: 'sandbox' | 'production';
  status:
    | 'sandbox_record_created'
    | 'dns_pending'
    | 'published'
    | 'not_configured'
    | 'failed';
  record_id: string | null;
  public_url: string | null;
  fallback_url: string | null;
  note: string;
}
