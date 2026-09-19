import type {
  Accepted,
  Artifact,
  ErrorEnvelope,
  Health,
  Profile,
  Publication,
  PublishRequest,
  Run,
  RunStatus,
} from '../types';

const TERMINAL: RunStatus[] = ['succeeded', 'partial', 'failed'];
const TOKEN_PREFIX = 'trendpilot.run-token.';

export class ApiClientError extends Error {
  code: string;
  retryable: boolean;
  status: number | null;

  constructor(message: string, code = 'CLIENT_ERROR', retryable = false, status: number | null = null) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.retryable = retryable;
    this.status = status;
  }
}

export interface RunFiles {
  oldExport?: File;
  currentExport?: File;
}

export interface CreateRunOptions {
  idempotencyKey?: string;
  signal?: AbortSignal;
}

export interface PollOptions {
  signal?: AbortSignal;
  intervalMs?: number;
  onUpdate?: (run: Run) => void;
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
}

function sessionStore(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.sessionStorage : null;
  } catch {
    return null;
  }
}

export function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  const random = new Uint8Array(24);
  crypto.getRandomValues(random);
  return Array.from(random, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export function saveRunToken(runId: string, accessToken: string): void {
  sessionStore()?.setItem(`${TOKEN_PREFIX}${runId}`, accessToken);
}

export function getRunToken(runId: string): string | null {
  return sessionStore()?.getItem(`${TOKEN_PREFIX}${runId}`) ?? null;
}

async function parseError(response: Response): Promise<ApiClientError> {
  try {
    const payload = (await response.json()) as ErrorEnvelope;
    if (payload?.error?.message) {
      return new ApiClientError(
        payload.error.message,
        payload.error.code,
        payload.error.retryable,
        response.status,
      );
    }
  } catch {
    // Fall through to a generic transport-safe message.
  }
  return new ApiClientError(
    `요청에 실패했습니다. (HTTP ${response.status})`,
    'HTTP_ERROR',
    response.status >= 500,
    response.status,
  );
}

async function jsonRequest<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new ApiClientError('서버에 연결할 수 없습니다.', 'NETWORK_ERROR', true, null);
  }
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  return jsonRequest<Health>('/api/v1/health', { signal });
}

export async function createRun(
  profile: Profile,
  files: RunFiles = {},
  options: CreateRunOptions = {},
): Promise<Accepted> {
  const hasOld = Boolean(files.oldExport);
  const hasCurrent = Boolean(files.currentExport);
  if (hasOld !== hasCurrent) {
    throw new ApiClientError(
      'Instagram export는 이전/현재 ZIP 두 파일을 함께 선택해야 합니다.',
      'INCOMPLETE_EXPORT_PAIR',
      false,
      422,
    );
  }
  if (profile.sample_followers && (hasOld || hasCurrent)) {
    throw new ApiClientError(
      '합성 팔로워 예제와 실제 ZIP 업로드는 동시에 사용할 수 없습니다.',
      'INVALID_PROFILE',
      false,
      422,
    );
  }
  if (hasOld && !profile.cloud_processing_consent) {
    throw new ApiClientError(
      '실제 ZIP을 처리하려면 cloud processing 동의가 필요합니다.',
      'CONSENT_REQUIRED',
      false,
      422,
    );
  }

  const body = new FormData();
  body.append('profile_json', JSON.stringify(profile));
  if (files.oldExport) body.append('old_export', files.oldExport);
  if (files.currentExport) body.append('current_export', files.currentExport);

  const accepted = await jsonRequest<Accepted>('/api/v1/runs', {
    method: 'POST',
    body,
    signal: options.signal,
    headers: {
      'Idempotency-Key': options.idempotencyKey ?? createIdempotencyKey(),
    },
  });
  saveRunToken(accepted.run_id, accepted.access_token);
  return accepted;
}

function authHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

export async function getRun(
  runId: string,
  accessToken: string,
  signal?: AbortSignal,
): Promise<Run> {
  return jsonRequest<Run>(`/api/v1/runs/${encodeURIComponent(runId)}`, {
    headers: authHeaders(accessToken),
    signal,
  });
}

function defaultSleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timer);
        reject(new DOMException('Aborted', 'AbortError'));
      },
      { once: true },
    );
  });
}

export async function pollRun(
  runId: string,
  accessToken: string,
  options: PollOptions = {},
): Promise<Run> {
  const intervalMs = options.intervalMs ?? 1500;
  const sleep = options.sleep ?? defaultSleep;
  while (true) {
    const run = await getRun(runId, accessToken, options.signal);
    options.onUpdate?.(run);
    if (TERMINAL.includes(run.status)) return run;
    await sleep(intervalMs, options.signal);
  }
}

function validateArtifactPath(runId: string, artifact: Artifact): void {
  const expectedPrefix = `/api/v1/runs/${encodeURIComponent(runId)}/artifacts/`;
  if (!artifact.path.startsWith(expectedPrefix)) {
    throw new ApiClientError(
      '백엔드가 반환한 artifact 경로가 허용된 run 범위를 벗어났습니다.',
      'INVALID_ARTIFACT_PATH',
    );
  }
  const pathname = artifact.path.split('?')[0];
  const fileName = decodeURIComponent(pathname.slice(pathname.lastIndexOf('/') + 1));
  if (fileName !== artifact.name) {
    throw new ApiClientError(
      '백엔드 artifact 이름과 다운로드 경로가 일치하지 않습니다.',
      'INVALID_ARTIFACT_PATH',
    );
  }
}

export async function fetchArtifactBlob(
  runId: string,
  artifact: Artifact,
  accessToken: string,
  signal?: AbortSignal,
): Promise<Blob> {
  validateArtifactPath(runId, artifact);
  let response: Response;
  try {
    response = await fetch(artifact.path, {
      headers: authHeaders(accessToken),
      signal,
    });
  } catch {
    throw new ApiClientError('artifact 다운로드 서버에 연결할 수 없습니다.', 'NETWORK_ERROR', true);
  }
  if (!response.ok) throw await parseError(response);
  return response.blob();
}

export async function downloadArtifact(
  runId: string,
  artifact: Artifact,
  accessToken: string,
): Promise<void> {
  const blob = await fetchArtifactBlob(runId, artifact, accessToken);
  const href = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = href;
    anchor.download = artifact.name;
    anchor.rel = 'noopener';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(href);
  }
}

export async function publishRun(
  runId: string,
  accessToken: string,
  request: PublishRequest,
  signal?: AbortSignal,
): Promise<Publication> {
  return jsonRequest<Publication>(`/api/v1/runs/${encodeURIComponent(runId)}/publish`, {
    method: 'POST',
    headers: {
      ...authHeaders(accessToken),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
    signal,
  });
}
