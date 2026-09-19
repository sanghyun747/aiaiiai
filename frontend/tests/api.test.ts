import { describe, expect, it, vi } from 'vitest';
import type { Accepted, Profile, Run } from '../src/types';
import {
  createRun,
  fetchArtifactBlob,
  pollRun,
} from '../src/lib/api';
import { mockRun } from '../src/mock/runSample';

const profile: Profile = {
  niche: '학습',
  audience: '학생',
  goal: 'views',
  format: 'instagram_reel',
  weekly_minutes: 90,
  query: '공부 루틴',
  data_mode: 'demo',
  sample_followers: false,
  pair_is_consecutive: true,
  cloud_processing_consent: true,
};

const accepted: Accepted = {
  contract_version: '1.1.0',
  run_id: 'run-123',
  access_token: 'x'.repeat(32),
  status: 'queued',
};

describe('API client', () => {
  it('serializes multipart profile_json and ZIP pair without setting multipart Content-Type', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(accepted), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const oldExport = new File(['old'], 'old.zip', { type: 'application/zip' });
    const currentExport = new File(['current'], 'current.zip', { type: 'application/zip' });
    const testIdempotencyKey = ['test', 'idempotency', 'key', 'fixture'].join('-');
    await createRun(profile, { oldExport, currentExport }, { idempotencyKey: testIdempotencyKey });

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/runs');
    expect(init.method).toBe('POST');
    expect(init.body).toBeInstanceOf(FormData);
    const body = init.body as FormData;
    expect(JSON.parse(String(body.get('profile_json')))).toEqual(profile);
    expect((body.get('old_export') as File).name).toBe('old.zip');
    expect((body.get('current_export') as File).name).toBe('current.zip');
    const headers = new Headers(init.headers);
    expect(headers.get('Idempotency-Key')).toBe(testIdempotencyKey);
    expect(headers.has('Content-Type')).toBe(false);
  });

  it('rejects a one-sided export pair before network access', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await expect(
      createRun(profile, { oldExport: new File(['old'], 'old.zip') }),
    ).rejects.toMatchObject({ code: 'INCOMPLETE_EXPORT_PAIR' });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('polls actual queued/running statuses until terminal success', async () => {
    const queued: Run = { ...mockRun, is_mock: false, status: 'queued', stage: 'validate', result: null };
    const running: Run = { ...mockRun, is_mock: false, status: 'running', stage: 'analyze', result: null };
    const success: Run = { ...mockRun, is_mock: false, status: 'succeeded', stage: 'done' };
    const updates: string[] = [];
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(queued), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(running), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(success), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const final = await pollRun('run-123', 'secret-token', {
      intervalMs: 1500,
      sleep: async () => undefined,
      onUpdate: (run) => updates.push(`${run.status}:${run.stage}`),
    });
    expect(final.status).toBe('succeeded');
    expect(updates).toEqual(['queued:validate', 'running:analyze', 'succeeded:done']);
    for (const call of fetchMock.mock.calls) {
      const headers = new Headers((call[1] as RequestInit).headers);
      expect(headers.get('Authorization')).toBe('Bearer secret-token');
    }
  });

  it('downloads returned artifact using bearer auth and never token in URL', async () => {
    const artifact = mockRun.result!.artifacts[0];
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('# report', { status: 200, headers: { 'Content-Type': 'text/markdown' } }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const blob = await fetchArtifactBlob(mockRun.run_id, artifact, 'private-token');
    expect(await blob.text()).toBe('# report');
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(artifact.path);
    expect(url).not.toContain('private-token');
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer private-token');
  });
});
