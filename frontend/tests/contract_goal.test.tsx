import { execFileSync } from 'node:child_process';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';
import { createRun, fetchArtifactBlob, pollRun } from '../src/lib/api';
import { buildChildrenAnimationBundle } from '../src/lib/comfyui';
import { mockRun, parseRunFixture } from '../src/mock/runSample';
import type { Profile, Run } from '../src/types';

const profile: Profile = {
  niche: '학습',
  audience: '학생',
  goal: 'views',
  format: 'instagram_reel',
  weekly_minutes: 60,
  query: '공부 루틴',
  data_mode: 'demo',
  sample_followers: true,
  pair_is_consecutive: true,
  cloud_processing_consent: false,
};

describe('Session A acceptance contract', () => {
  it('test_contract__goal__all_five_production_package_areas_and', () => {
    render(<App initialRun={mockRun} forceMock />);
    expect(screen.getAllByText('SCRIPT')).toHaveLength(3);
    expect(screen.getAllByText('SHOT LIST')).toHaveLength(3);
    expect(screen.getAllByText('EDITING GUIDE')).toHaveLength(3);
    expect(screen.getAllByText('THUMBNAIL PLAN')).toHaveLength(3);
    expect(screen.getAllByText('PUBLISHING PACKAGE')).toHaveLength(3);
    expect(screen.getAllByRole('button', { name: /복사/ }).length).toBeGreaterThanOrEqual(15);
  });

  it('test_contract__goal__child_animation_comfyui_sangh_handoff_error', async () => {
    const user = userEvent.setup();
    render(<App initialRun={mockRun} forceMock />);
    await user.click(screen.getByLabelText(/어린이용 애니메이션 콘텐츠/));
    expect(screen.getAllByText('ComfyUI | sangh · 어린이 애니메이션 핸드오프')).toHaveLength(3);
    const bundle = buildChildrenAnimationBundle(mockRun.result!.actions[0]);
    expect(bundle.workflow).toContain('cogvideox_5b_i2v_q4_rtx4060_minimal');
    expect(bundle.scenePrompts).toHaveLength(mockRun.result!.actions[0].production_package.shot_list.length);
  });

  it('test_contract__goal__commit_and_push_only_frontend_owned', () => {
    const status = execFileSync('git', ['status', '--porcelain=v1', '--untracked-files=all'], {
      cwd: '..',
      encoding: 'utf8',
    });
    const lines = status.split(/\r?\n/).filter(Boolean);
    expect(lines.every((line) => {
      const path = line.slice(3).replace(/^"|"$/g, '');
      return path.startsWith('frontend/');
    })).toBe(true);
    expect(lines.some((line) => line.startsWith(' D') || line.startsWith('D '))).toBe(false);
    expect(execFileSync('git', ['branch', '--show-current'], { cwd: '..', encoding: 'utf8' }).trim()).toBe('feat/frontend');
    expect(execFileSync('git', ['remote', 'get-url', 'aiaiiai'], { cwd: '..', encoding: 'utf8' }).trim()).toContain('sanghyun747/aiaiiai.git');
  });

  it('test_contract__goal__exactly_3_successful_actions_with_safe', () => {
    const run = parseRunFixture(mockRun);
    const actions = run.result!.actions;
    expect(actions).toHaveLength(3);
    expect(actions.some((action) => action.strategy_mode === 'safe_bet')).toBe(true);
    const growth = actions.filter((action) => action.strategy_mode === 'growth_experiment');
    expect(growth.length).toBeGreaterThanOrEqual(1);
    expect(growth.every((action) => Boolean(action.weakness_target))).toBe(true);
  });

  it('test_contract__goal__finish_trendpilot_session_a_frontend_contract', async () => {
    const accepted = {
      contract_version: '1.1.0' as const,
      run_id: 'run-acceptance',
      access_token: 'x'.repeat(32),
      status: 'queued' as const,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(accepted), { status: 202, headers: { 'Content-Type': 'application/json' } }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const testIdempotencyKey = ['acceptance', 'test', 'key', 'fixture'].join('-');
    await createRun(profile, {}, { idempotencyKey: testIdempotencyKey });
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const form = init.body as FormData;
    expect(JSON.parse(String(form.get('profile_json')))).toEqual(profile);
    expect(new Headers(init.headers).has('Content-Type')).toBe(false);
  });

  it('test_contract__goal__korean_dashboard_with_conservative_follower_categories', () => {
    render(<App initialRun={mockRun} forceMock />);
    for (const label of ['Raw missing', 'Relationship absent', 'Username rename', 'Outside export window', 'Unresolved']) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText(/“언팔한 사람 수”가 아닙니다/)).toBeInTheDocument();
    expect(screen.getByText(/인과관계도 이 데이터로 판단하지 않습니다/)).toBeInTheDocument();
  });

  it('test_contract__goal__real_status_polling_and_bearer_artifact', async () => {
    const queued: Run = { ...mockRun, is_mock: false, status: 'queued', stage: 'validate', result: null };
    const running: Run = { ...mockRun, is_mock: false, status: 'running', stage: 'render', result: null };
    const done: Run = { ...mockRun, is_mock: false };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(queued), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(running), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(done), { status: 200 }))
      .mockResolvedValueOnce(new Response('artifact', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const states: string[] = [];
    await pollRun('sample-run-001', 'secret', {
      sleep: async () => undefined,
      onUpdate: (run) => states.push(run.status),
    });
    expect(states).toEqual(['queued', 'running', 'succeeded']);
    await fetchArtifactBlob('sample-run-001', mockRun.result!.artifacts[0], 'secret');
    const artifactCall = fetchMock.mock.calls[3] as [string, RequestInit];
    expect(artifactCall[0]).not.toContain('secret');
    expect(new Headers(artifactCall[1].headers).get('Authorization')).toBe('Bearer secret');
  });

  it('test_contract__goal__typed_mock_fixture_with_no_silent', async () => {
    expect(parseRunFixture(mockRun).is_mock).toBe(true);
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        contract_version: '1.1.0',
        error: { code: 'PROVIDER_UNAVAILABLE', message: 'backend unavailable', retryable: true },
      }), { status: 503, headers: { 'Content-Type': 'application/json' } }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    render(<App forceMock={false} />);
    await user.click(screen.getByRole('button', { name: '분석 Run 시작' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('PROVIDER_UNAVAILABLE');
    expect(screen.queryByText('콘텐츠 전략')).not.toBeInTheDocument();
    expect(screen.queryByText(/fixture 기반 화면 개발 모드/)).not.toBeInTheDocument();
  });
});
