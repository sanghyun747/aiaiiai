import { FormEvent, useMemo, useRef, useState } from 'react';
import type {
  Action,
  Artifact,
  Followers,
  Profile,
  Publication,
  Result,
  Run,
  Trace,
} from './types';
import {
  ApiClientError,
  createIdempotencyKey,
  createRun,
  downloadArtifact,
  pollRun,
  publishRun,
} from './lib/api';
import {
  buildChildrenAnimationBundle,
  checkComfyUi,
  comfyPublicUrl,
  type ComfyStatus,
} from './lib/comfyui';
import { runMock } from './mock/runSample';

const ENV_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

const initialProfile: Profile = {
  niche: '학습·생산성',
  audience: '공부 습관을 만들고 싶은 18–29세',
  goal: 'views',
  format: 'instagram_reel',
  weekly_minutes: 120,
  query: '공부 루틴 생산성',
  data_mode: 'demo',
  sample_followers: true,
  pair_is_consecutive: true,
  cloud_processing_consent: false,
};

type FollowersMode = 'sample' | 'upload' | 'none';

interface AppProps {
  initialRun?: Run | null;
  forceMock?: boolean;
}

function unknown(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === '' ? '미확인' : String(value);
}

function modeLabel(run: Run): string {
  if (run.is_mock) return 'MOCK 실행';
  const modes = new Set(run.trace.map((trace) => trace.mode));
  if (modes.has('mock')) return '일부 MOCK 포함';
  if (modes.has('cached')) return '캐시 근거 포함';
  return '실제 실행';
}

function stageLabel(stage: Run['stage']): string {
  return {
    validate: '입력 검증',
    plan: '분석 계획',
    analyze: '계정·근거 분석',
    recommend: '콘텐츠 전략 생성',
    render: '제작 패키지·artifact 생성',
    done: '완료',
  }[stage];
}

function statusLabel(status: Run['status']): string {
  return {
    queued: '대기 중',
    running: '처리 중',
    succeeded: '성공',
    partial: '부분 완료',
    failed: '실패',
  }[status];
}

async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}

function CopyButton({ value, label = '복사' }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="copy-button"
      type="button"
      onClick={async () => {
        await copyText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1000);
      }}
    >
      {copied ? '복사됨' : label}
    </button>
  );
}

function EvidenceSection({ result }: { result: Result }) {
  const sourceMap = new Map(result.sources.map((source) => [source.id, source]));
  return (
    <section className="panel" aria-labelledby="evidence-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">OBSERVATION</p>
          <h2 id="evidence-title">관측 근거와 현재 기회</h2>
        </div>
        <span className="mode-chip">{result.evidence_mode}</span>
      </div>

      {result.sample_notice && <div className="notice warning">{result.sample_notice}</div>}

      <div className="source-grid">
        {result.sources.map((source) => (
          <article className="source-card" key={source.id}>
            <div className="card-topline">
              <span>{source.platform}</span>
              <span>{source.source_mode}</span>
            </div>
            <h3>{source.title}</h3>
            <dl className="compact-dl">
              <div><dt>관측 시각</dt><dd>{source.observed_at}</dd></div>
              <div><dt>조회수</dt><dd>{unknown(source.views)}</dd></div>
            </dl>
            <p className="muted">{source.note}</p>
            {source.url?.startsWith('https://') && (
              <a href={source.url} target="_blank" rel="noopener noreferrer">원본 근거 열기 ↗</a>
            )}
          </article>
        ))}
      </div>

      <div className="opportunity-grid">
        {result.opportunities.map((opportunity) => (
          <article className="opportunity-card" key={opportunity.id}>
            <p className="eyebrow">CURRENT OPPORTUNITY</p>
            <h3>{opportunity.title}</h3>
            <p>{opportunity.reason}</p>
            <p className="metric-line">
              평균 조회/시간 <strong>{unknown(opportunity.mean_views_per_hour)}</strong>
              <span> · </span>
              근거 <strong>{opportunity.momentum_evidence}</strong>
            </p>
            {opportunity.momentum_evidence === 'single_observation' && (
              <p className="muted">단일 관측값은 상승 속도·가속을 입증하지 않습니다.</p>
            )}
            <div className="source-tags">
              {opportunity.source_ids.map((id) => (
                <span key={id}>{sourceMap.get(id)?.title ?? id}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function FollowersSection({ followers }: { followers: Followers | null }) {
  if (!followers) {
    return (
      <section className="panel" aria-labelledby="followers-title">
        <p className="eyebrow">FOLLOWER AUDIT</p>
        <h2 id="followers-title">팔로워 변화</h2>
        <div className="empty-state">미확인</div>
        <p className="muted">ZIP pair가 없으면 팔로워 이력은 0이 아니라 미확인입니다.</p>
      </section>
    );
  }

  const categories = [
    ['Raw missing', followers.raw_missing_count, '이전 export에만 보이는 원시 누락'],
    ['Relationship absent', followers.relationship_absent_count, '감사 근거가 관계 부재를 허용한 항목'],
    ['Username rename', followers.renamed_still_following_count, 'export 연속성 등으로 확인된 계정명 변경'],
    ['Outside export window', followers.outside_window_count, '안전한 비교 기간 밖의 항목'],
    ['Unresolved', followers.unresolved_count, '계정명 변경 등을 배제하지 못한 미확인 항목'],
  ] as const;

  return (
    <section className="panel" aria-labelledby="followers-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">FOLLOWER AUDIT</p>
          <h2 id="followers-title">팔로워 변화</h2>
        </div>
        <span className="mode-chip">{followers.input_kind === 'synthetic' ? '합성 예제' : '사용자 ZIP'}</span>
      </div>

      <div className="follower-overview">
        <div><span>이전 export</span><strong>{followers.old_count}</strong></div>
        <div><span>현재 export</span><strong>{followers.current_count}</strong></div>
        <div><span>export 개수 차이</span><strong>{followers.export_count_delta}</strong></div>
        <div><span>새로 관측된 handle</span><strong>{followers.new_observed_excluding_renames}</strong></div>
      </div>

      <div className="audit-grid">
        {categories.map(([name, count, description]) => (
          <article key={name} className="audit-card">
            <span>{name}</span>
            <strong>{count}</strong>
            <p>{description}</p>
          </article>
        ))}
      </div>
      <div className="notice neutral">
        <strong>해석 주의:</strong> old-current 개수 차이는 검증된 순성장이나 “언팔한 사람 수”가 아닙니다.
        특정 게시물이 관계 부재를 일으켰다는 인과관계도 이 데이터로 판단하지 않습니다.
      </div>
      <p className="muted">{followers.scope_note}</p>
    </section>
  );
}

function ScriptView({ action }: { action: Action }) {
  const script = action.production_package.script;
  return (
    <div className="package-section">
      <div className="package-title"><h4>SCRIPT</h4><CopyButton value={[script.hook, script.intro, ...script.body, script.ending, script.cta].join('\n\n')} /></div>
      <dl className="field-list">
        <div><dt>Hook</dt><dd>{script.hook}</dd></div>
        <div><dt>Intro</dt><dd>{script.intro}</dd></div>
        <div><dt>Body</dt><dd><ol>{script.body.map((line) => <li key={line}>{line}</li>)}</ol></dd></div>
        <div><dt>Ending</dt><dd>{script.ending}</dd></div>
        <div><dt>CTA</dt><dd>{script.cta}</dd></div>
      </dl>
    </div>
  );
}

function ShotListView({ action }: { action: Action }) {
  const shots = action.production_package.shot_list;
  return (
    <div className="package-section">
      <div className="package-title"><h4>SHOT LIST</h4><CopyButton value={shots.map((s) => `${s.order}. ${s.duration_sec}s | ${s.visual} | ${s.narration} | ${s.subtitle}`).join('\n')} /></div>
      <div className="shot-table-wrap">
        <table>
          <thead><tr><th>#</th><th>시간</th><th>화면</th><th>내레이션</th><th>자막</th></tr></thead>
          <tbody>{shots.map((shot) => (
            <tr key={shot.order}>
              <td>{shot.order}</td><td>{shot.duration_sec}초</td><td>{shot.visual}</td><td>{shot.narration}</td><td>{shot.subtitle}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function EditingView({ action }: { action: Action }) {
  const editing = action.production_package.editing_plan;
  const text = [editing.pace, editing.caption_style, editing.cut_plan, editing.music_direction, ...editing.b_roll_notes].join('\n');
  return (
    <div className="package-section">
      <div className="package-title"><h4>EDITING GUIDE</h4><CopyButton value={text} /></div>
      <dl className="field-list">
        <div><dt>영상 속도</dt><dd>{editing.pace}</dd></div>
        <div><dt>자막 스타일</dt><dd>{editing.caption_style}</dd></div>
        <div><dt>컷 구성</dt><dd>{editing.cut_plan}</dd></div>
        <div><dt>음악 방향</dt><dd>{editing.music_direction}</dd></div>
        <div><dt>B-roll</dt><dd><ul>{editing.b_roll_notes.map((item) => <li key={item}>{item}</li>)}</ul></dd></div>
      </dl>
    </div>
  );
}

function ThumbnailView({ action }: { action: Action }) {
  const thumbnail = action.production_package.thumbnail_plan;
  return (
    <div className="package-section">
      <div className="package-title"><h4>THUMBNAIL PLAN</h4><CopyButton value={thumbnail.generation_prompt} label="프롬프트 복사" /></div>
      <dl className="field-list">
        <div><dt>콘셉트</dt><dd>{thumbnail.concept}</dd></div>
        <div><dt>썸네일 문구</dt><dd>{thumbnail.text}</dd></div>
        <div><dt>화면 구성</dt><dd>{thumbnail.composition}</dd></div>
        <div><dt>생성용 프롬프트</dt><dd>{thumbnail.generation_prompt}</dd></div>
      </dl>
    </div>
  );
}

function PublishingView({ action }: { action: Action }) {
  const publishing = action.production_package.publishing_package;
  const text = [publishing.title, publishing.description, publishing.hashtags.join(' '), publishing.cta, publishing.target_metric, publishing.posting_notes].join('\n\n');
  return (
    <div className="package-section">
      <div className="package-title"><h4>PUBLISHING PACKAGE</h4><CopyButton value={text} /></div>
      <dl className="field-list">
        <div><dt>제목</dt><dd>{publishing.title}</dd></div>
        <div><dt>설명</dt><dd>{publishing.description}</dd></div>
        <div><dt>해시태그</dt><dd>{publishing.hashtags.join(' ')}</dd></div>
        <div><dt>CTA</dt><dd>{publishing.cta}</dd></div>
        <div><dt>목표 지표</dt><dd>{publishing.target_metric}</dd></div>
        <div><dt>게시 참고사항</dt><dd>{publishing.posting_notes}</dd></div>
      </dl>
    </div>
  );
}

function ComfyAnimationView({ action }: { action: Action }) {
  const bundle = useMemo(() => buildChildrenAnimationBundle(action), [action]);
  const allScenes = bundle.scenePrompts.join('\n\n');
  return (
    <div className="comfy-box">
      <div className="package-title">
        <div>
          <p className="eyebrow">LOCAL PRODUCTION ASSIST</p>
          <h4>ComfyUI | sangh · 어린이 애니메이션 핸드오프</h4>
        </div>
        <CopyButton value={[bundle.characterPrompt, allScenes, bundle.thumbnailPrompt].join('\n\n')} label="전체 프롬프트 복사" />
      </div>
      <p className="muted">
        Production Package를 로컬 CogVideoX i2v 제작에 옮기기 위한 프롬프트입니다.
        TrendPilot이 영상을 렌더링했다고 주장하지 않으며 실제 생성은 ComfyUI에서 실행합니다.
      </p>
      <p><strong>권장 workflow:</strong> {bundle.workflow}</p>
      <details>
        <summary>캐릭터 일관성 프롬프트</summary>
        <pre>{bundle.characterPrompt}</pre>
        <CopyButton value={bundle.characterPrompt} />
      </details>
      <details>
        <summary>장면별 프롬프트 ({bundle.scenePrompts.length})</summary>
        {bundle.scenePrompts.map((prompt, index) => (
          <div className="prompt-block" key={prompt}>
            <strong>Scene {index + 1}</strong><pre>{prompt}</pre><CopyButton value={prompt} />
          </div>
        ))}
      </details>
      <details>
        <summary>썸네일 생성 프롬프트</summary>
        <pre>{bundle.thumbnailPrompt}</pre>
        <CopyButton value={bundle.thumbnailPrompt} />
      </details>
      <ul className="safety-list">{bundle.safetyNotes.map((note) => <li key={note}>{note}</li>)}</ul>
    </div>
  );
}

function ActionCard({ action, sources, childrenAnimation }: { action: Action; sources: Result['sources']; childrenAnimation: boolean }) {
  const sourceMap = new Map(sources.map((source) => [source.id, source]));
  const isGrowth = action.strategy_mode === 'growth_experiment';
  return (
    <article className="action-card">
      <div className="action-head">
        <div>
          <span className={isGrowth ? 'strategy growth' : 'strategy safe'}>
            {isGrowth ? 'GROWTH EXPERIMENT' : 'SAFE BET'}
          </span>
          <h3>{action.title}</h3>
        </div>
        <span className="time-budget">{action.production_minutes}분</span>
      </div>
      {isGrowth && (
        <div className="weakness"><strong>weakness_target</strong><span>{unknown(action.weakness_target)}</span></div>
      )}
      <p>{action.fit_reason}</p>
      <div className="hook-grid">
        <div><strong>Hook A</strong><p>{action.hook_a}</p><CopyButton value={action.hook_a} /></div>
        <div><strong>Hook B</strong><p>{action.hook_b}</p><CopyButton value={action.hook_b} /></div>
      </div>
      <dl className="compact-dl action-meta">
        <div><dt>CTA</dt><dd>{action.cta}</dd></div>
        <div><dt>목표 지표</dt><dd>{action.metric}</dd></div>
        <div><dt>기준값</dt><dd>{unknown(action.baseline)}</dd></div>
        <div><dt>성공 규칙</dt><dd>{action.success_rule}</dd></div>
      </dl>
      <div className="source-tags">
        {action.source_ids.map((id) => {
          const source = sourceMap.get(id);
          return source?.url?.startsWith('https://') ? (
            <a key={id} href={source.url} target="_blank" rel="noopener noreferrer">{source.title} ↗</a>
          ) : <span key={id}>{source?.title ?? id}</span>;
        })}
      </div>

      <div className="production-package" aria-label={`${action.title} Production Package`}>
        <h4 className="package-heading">Production Package</h4>
        <p className="muted">촬영만 수행하면 바로 제작에 옮길 수 있도록 다섯 영역을 제공합니다.</p>
        <ScriptView action={action} />
        <ShotListView action={action} />
        <EditingView action={action} />
        <ThumbnailView action={action} />
        <PublishingView action={action} />
        {childrenAnimation && <ComfyAnimationView action={action} />}
      </div>
    </article>
  );
}

function TracePanel({ trace }: { trace: Trace[] }) {
  return (
    <section className="panel">
      <p className="eyebrow">EXECUTION TRACE</p>
      <h2>실행 근거</h2>
      <div className="trace-list">
        {trace.map((item, index) => (
          <div className="trace-item" key={`${item.provider}-${item.operation}-${index}`}>
            <div><strong>{item.provider}</strong><span>{item.operation}</span></div>
            <span className="mode-chip">{item.mode}</span>
            <span>{item.status}</span>
            <p>{item.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ArtifactsPanel({
  run,
  downloading,
  onDownload,
}: {
  run: Run;
  downloading: string | null;
  onDownload: (artifact: Artifact) => Promise<void>;
}) {
  if (!run.result) return null;
  return (
    <section className="panel">
      <p className="eyebrow">DAYTONA ARTIFACTS</p>
      <h2>생성 파일 다운로드</h2>
      <p className="muted">백엔드가 실제로 반환하고 검증한 artifact만 표시합니다. Bearer token은 URL에 넣지 않습니다.</p>
      {run.result.artifacts.length === 0 ? (
        <div className="empty-state">반환된 artifact 없음</div>
      ) : (
        <div className="artifact-list">
          {run.result.artifacts.map((artifact) => (
            <div key={artifact.name}>
              <div><strong>{artifact.name}</strong><code>{artifact.sha256.slice(0, 12)}…</code></div>
              <button
                type="button"
                disabled={run.is_mock || downloading === artifact.name}
                onClick={() => void onDownload(artifact)}
              >
                {run.is_mock ? 'MOCK에서는 다운로드 안 함' : downloading === artifact.name ? '다운로드 중…' : '인증 다운로드'}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ResultDashboard({
  run,
  childrenAnimation,
  downloading,
  onDownload,
}: {
  run: Run;
  childrenAnimation: boolean;
  downloading: string | null;
  onDownload: (artifact: Artifact) => Promise<void>;
}) {
  if (!run.result) {
    return <section className="panel"><div className="empty-state">결과 데이터가 없습니다.</div></section>;
  }
  const { result } = run;
  const invalidSuccess = run.status === 'succeeded' && (
    result.actions.length !== 3 ||
    !result.actions.some((action) => action.strategy_mode === 'safe_bet') ||
    !result.actions.some((action) => action.strategy_mode === 'growth_experiment') ||
    result.actions.some((action) => action.strategy_mode === 'growth_experiment' && !action.weakness_target)
  );

  if (invalidSuccess) {
    return (
      <section className="panel">
        <div className="notice error">
          성공 응답이 contract 1.1.0의 action 불변식(정확히 3개, SAFE BET/GROWTH EXPERIMENT, weakness_target)을 만족하지 않습니다.
        </div>
      </section>
    );
  }

  return (
    <>
      <EvidenceSection result={result} />
      <FollowersSection followers={result.followers} />
      <section className="panel" aria-labelledby="strategy-title">
        <div className="section-heading">
          <div><p className="eyebrow">NEXT 3 ACTIONS</p><h2 id="strategy-title">콘텐츠 전략</h2></div>
          <span className="mode-chip">{result.actions.length} actions</span>
        </div>
        <div className="actions-stack">
          {result.actions.map((action) => (
            <ActionCard key={action.id} action={action} sources={result.sources} childrenAnimation={childrenAnimation} />
          ))}
        </div>
      </section>
      <ArtifactsPanel run={run} downloading={downloading} onDownload={onDownload} />
      <TracePanel trace={run.trace} />
      <section className="panel">
        <p className="eyebrow">LIMITATIONS</p>
        <h2>한계 / 미확인 정보</h2>
        <ul>{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      </section>
    </>
  );
}

export function App({ initialRun = null, forceMock }: AppProps) {
  const useMock = forceMock ?? ENV_MOCK;
  const [profile, setProfile] = useState<Profile>(initialProfile);
  const [followersMode, setFollowersMode] = useState<FollowersMode>('sample');
  const [oldExport, setOldExport] = useState<File | undefined>();
  const [currentExport, setCurrentExport] = useState<File | undefined>();
  const [run, setRun] = useState<Run | null>(initialRun);
  const [busy, setBusy] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [childrenAnimation, setChildrenAnimation] = useState(false);
  const [comfyStatus, setComfyStatus] = useState<ComfyStatus | null>(null);
  const [publishConsent, setPublishConsent] = useState(false);
  const [publication, setPublication] = useState<Publication | null>(null);
  const [publishing, setPublishing] = useState(false);
  const idempotency = useRef<{ fingerprint: string; key: string } | null>(null);
  const tokenRef = useRef<string | null>(null);

  const profileForSubmit = useMemo<Profile>(() => ({
    ...profile,
    sample_followers: followersMode === 'sample',
    pair_is_consecutive: followersMode === 'upload' ? profile.pair_is_consecutive : true,
    cloud_processing_consent: followersMode === 'upload' ? profile.cloud_processing_consent : false,
  }), [followersMode, profile]);

  const fingerprint = JSON.stringify({
    profile: profileForSubmit,
    old: oldExport ? [oldExport.name, oldExport.size, oldExport.lastModified] : null,
    current: currentExport ? [currentExport.name, currentExport.size, currentExport.lastModified] : null,
  });

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setUiError(null);
    setPublication(null);
    setBusy(true);
    try {
      if (useMock) {
        tokenRef.current = null;
        const mockResult = await runMock(setRun);
        setRun(mockResult);
        return;
      }
      if (followersMode === 'upload' && (!oldExport || !currentExport)) {
        throw new ApiClientError('실제 export는 이전/현재 ZIP pair를 모두 선택해야 합니다.', 'INCOMPLETE_EXPORT_PAIR');
      }
      if (followersMode === 'upload' && !profileForSubmit.cloud_processing_consent) {
        throw new ApiClientError('클라우드 처리 동의를 직접 선택해야 실제 ZIP을 전송할 수 있습니다.', 'CONSENT_REQUIRED');
      }
      const same = idempotency.current?.fingerprint === fingerprint;
      const key = same ? idempotency.current!.key : createIdempotencyKey();
      idempotency.current = { fingerprint, key };

      const accepted = await createRun(
        profileForSubmit,
        followersMode === 'upload' ? { oldExport, currentExport } : {},
        { idempotencyKey: key },
      );
      tokenRef.current = accepted.access_token;
      const terminal = await pollRun(accepted.run_id, accepted.access_token, {
        onUpdate: setRun,
      });
      setRun(terminal);
      idempotency.current = null;
    } catch (error) {
      if (error instanceof ApiClientError) {
        setUiError(`${error.code}: ${error.message}`);
      } else {
        setUiError(error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.');
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload(artifact: Artifact) {
    if (!run || !tokenRef.current) {
      setUiError('이 브라우저 세션에 artifact 인증 token이 없습니다.');
      return;
    }
    setUiError(null);
    setDownloading(artifact.name);
    try {
      await downloadArtifact(run.run_id, artifact, tokenRef.current);
    } catch (error) {
      setUiError(error instanceof Error ? error.message : 'artifact 다운로드 실패');
    } finally {
      setDownloading(null);
    }
  }

  async function handlePublish() {
    if (!run || !tokenRef.current || !publishConsent) return;
    setPublishing(true);
    setUiError(null);
    try {
      const next = await publishRun(run.run_id, tokenRef.current, {
        environment: 'sandbox',
        publish_consent: true,
      });
      setPublication(next);
    } catch (error) {
      setUiError(error instanceof Error ? error.message : '게시 요청 실패');
    } finally {
      setPublishing(false);
    }
  }

  const mockMismatch = run && run.is_mock !== useMock && useMock;
  const statusText = run ? `${statusLabel(run.status)} · ${stageLabel(run.stage)}` : '아직 실행하지 않음';

  return (
    <div className="app-shell">
      {useMock && <div className="mock-banner">MOCK · fixture 기반 화면 개발 모드 · 실제 Nosana/Daytona 실행 아님</div>}
      <header className="hero">
        <div>
          <p className="eyebrow">PERSONAL SNS GROWTH PRODUCTION AGENT</p>
          <h1>TrendPilot</h1>
          <p className="hero-copy">
            현재 근거와 계정 변화를 바탕으로 다음 콘텐츠 3개를 정하고,
            실제 촬영만 제외한 제작 준비물을 완성합니다.
          </p>
        </div>
        <div className="status-card">
          <span>현재 상태</span>
          <strong>{statusText}</strong>
          {run && <small>{modeLabel(run)} · evidence {run.result?.evidence_mode ?? '미확인'}</small>}
        </div>
      </header>

      {mockMismatch && <div className="notice error">MOCK 환경에서 live run을 주입했습니다. 모드 표시를 확인하세요.</div>}
      {uiError && <div className="notice error" role="alert">{uiError}</div>}
      {run?.status === 'partial' && <div className="notice warning">부분 완료 상태입니다. 확인된 결과만 표시하며 누락된 항목을 성공으로 간주하지 않습니다.</div>}
      {run?.status === 'failed' && <div className="notice error">실행 실패: {run.error?.message ?? '미확인 오류'}</div>}

      <form className="panel input-panel" onSubmit={handleSubmit}>
        <div className="section-heading">
          <div><p className="eyebrow">INPUT</p><h2>이번 콘텐츠 실험 설정</h2></div>
          <span className="contract-chip">API contract 1.1.0</span>
        </div>

        <div className="form-grid">
          <label>주제 / niche
            <input value={profile.niche} onChange={(e) => setProfile({ ...profile, niche: e.target.value })} required />
          </label>
          <label>대상 / audience
            <input value={profile.audience} onChange={(e) => setProfile({ ...profile, audience: e.target.value })} required />
          </label>
          <label>목표
            <select value={profile.goal} onChange={(e) => setProfile({ ...profile, goal: e.target.value as Profile['goal'] })}>
              <option value="views">조회수</option><option value="followers">팔로워</option><option value="leads">문의/리드</option>
            </select>
          </label>
          <label>콘텐츠 형식
            <select value={profile.format} onChange={(e) => setProfile({ ...profile, format: e.target.value as Profile['format'] })}>
              <option value="instagram_reel">Instagram Reel</option><option value="youtube_short">YouTube Short</option>
            </select>
          </label>
          <label>주간 제작 가능 시간 (분)
            <input type="number" min={15} max={1200} value={profile.weekly_minutes} onChange={(e) => setProfile({ ...profile, weekly_minutes: Number(e.target.value) })} />
          </label>
          <label>트렌드 query
            <input value={profile.query} onChange={(e) => setProfile({ ...profile, query: e.target.value })} required />
          </label>
          <label>근거 모드
            <select value={profile.data_mode} onChange={(e) => setProfile({ ...profile, data_mode: e.target.value as Profile['data_mode'] })}>
              <option value="demo">Demo · 합성 trend input</option><option value="live">Live · 실제 source 요청</option>
            </select>
          </label>
        </div>

        <fieldset>
          <legend>팔로워 데이터</legend>
          <div className="radio-row">
            <label><input type="radio" name="followers-mode" checked={followersMode === 'sample'} onChange={() => setFollowersMode('sample')} /> 합성 예제</label>
            <label><input type="radio" name="followers-mode" checked={followersMode === 'none'} onChange={() => setFollowersMode('none')} /> 사용 안 함</label>
            <label><input type="radio" name="followers-mode" checked={followersMode === 'upload'} onChange={() => setFollowersMode('upload')} /> 실제 Instagram export ZIP pair</label>
          </div>
          {followersMode === 'upload' && (
            <div className="upload-box">
              <label>이전 export ZIP<input type="file" accept=".zip,application/zip" onChange={(e) => setOldExport(e.target.files?.[0])} /></label>
              <label>현재 export ZIP<input type="file" accept=".zip,application/zip" onChange={(e) => setCurrentExport(e.target.files?.[0])} /></label>
              <label className="check-line">
                <input type="checkbox" checked={profile.pair_is_consecutive} onChange={(e) => setProfile({ ...profile, pair_is_consecutive: e.target.checked })} />
                두 export가 시간상 연속 export임을 확인합니다.
              </label>
              <div className="notice neutral">
                최소화된 팔로워 데이터는 Daytona에서 처리되고, 집계값은 Nosana에 전달될 수 있습니다.
                원본 ZIP/handle을 Nosana에 보내지 않습니다.
              </div>
              <label className="check-line consent">
                <input type="checkbox" checked={profile.cloud_processing_consent} onChange={(e) => setProfile({ ...profile, cloud_processing_consent: e.target.checked })} />
                위 cloud processing 내용을 확인했고 이번 실행에 동의합니다.
              </label>
            </div>
          )}
        </fieldset>

        <fieldset>
          <legend>로컬 제작 보조</legend>
          <label className="check-line">
            <input type="checkbox" checked={childrenAnimation} onChange={(e) => setChildrenAnimation(e.target.checked)} />
            어린이용 애니메이션 콘텐츠 · ComfyUI | sangh 프롬프트 핸드오프 활성화
          </label>
          {childrenAnimation && (
            <div className="comfy-connect">
              <button type="button" onClick={async () => setComfyStatus(await checkComfyUi())}>ComfyUI 연결 확인</button>
              <a href={comfyPublicUrl()} target="_blank" rel="noopener noreferrer">ComfyUI | sangh 열기 ↗</a>
              {comfyStatus && <span className={comfyStatus.ok ? 'ok-text' : 'error-text'}>{comfyStatus.label} · {comfyStatus.detail}</span>}
            </div>
          )}
        </fieldset>

        <button className="primary" type="submit" disabled={busy}>
          {busy ? '실제 상태를 확인하는 중…' : useMock ? 'MOCK 결과 보기' : '분석 Run 시작'}
        </button>
        <p className="muted small">API 장애 시 MOCK으로 자동 전환하지 않습니다. Demo synthetic input을 실제 Nosana/Daytona에 실행한 경우도 MOCK과 별도로 표시합니다.</p>
      </form>

      {run && (
        <>
          <ResultDashboard run={run} childrenAnimation={childrenAnimation} downloading={downloading} onDownload={handleDownload} />

          <section className="panel">
            <p className="eyebrow">DNSIMPLE PUBLISH</p>
            <h2>게시 · 별도 동의</h2>
            <p className="muted">DNSimple sandbox는 실제 API 실행이어도 공개 DNS 접속 성공을 뜻하지 않습니다.</p>
            <label className="check-line consent">
              <input type="checkbox" checked={publishConsent} onChange={(e) => setPublishConsent(e.target.checked)} disabled={run.is_mock || run.status !== 'succeeded'} />
              sandbox 레코드 생성 요청에 동의합니다.
            </label>
            <button type="button" disabled={!publishConsent || run.is_mock || run.status !== 'succeeded' || publishing} onClick={() => void handlePublish()}>
              {publishing ? '게시 확인 중…' : 'DNSimple sandbox 게시'}
            </button>
            {publication?.status === 'sandbox_record_created' && (
              <div className="notice warning">DNSimple 테스트 레코드 생성 · 공개 접속 불가</div>
            )}
            {publication && <p>{publication.note}</p>}
          </section>
        </>
      )}

      <footer>
        <p>촬영은 사용자가 수행합니다. Production Package는 제작 지시이며 완성 영상 렌더링이나 성과를 보장하지 않습니다.</p>
      </footer>
    </div>
  );
}
