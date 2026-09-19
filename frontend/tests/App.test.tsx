import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { App } from '../src/App';
import { mockRun } from '../src/mock/runSample';
import type { Run } from '../src/types';

describe('TrendPilot dashboard', () => {
  it('labels MOCK clearly and renders the conservative follower categories', () => {
    render(<App initialRun={mockRun} forceMock />);
    expect(screen.getByText(/MOCK · fixture 기반 화면 개발 모드/)).toBeInTheDocument();
    expect(screen.getByText('Raw missing')).toBeInTheDocument();
    expect(screen.getByText('Relationship absent')).toBeInTheDocument();
    expect(screen.getByText('Username rename')).toBeInTheDocument();
    expect(screen.getByText('Outside export window')).toBeInTheDocument();
    expect(screen.getByText('Unresolved')).toBeInTheDocument();
    expect(screen.getByText(/“언팔한 사람 수”가 아닙니다/)).toBeInTheDocument();
  });

  it('renders exactly three strategies with SAFE BET, GROWTH EXPERIMENT and weakness target', () => {
    render(<App initialRun={mockRun} forceMock />);
    expect(screen.getAllByText('SAFE BET')).toHaveLength(2);
    expect(screen.getAllByText('GROWTH EXPERIMENT')).toHaveLength(1);
    expect(screen.getByText('weakness_target')).toBeInTheDocument();
    expect(screen.getByText('opening_hook')).toBeInTheDocument();
  });

  it('renders all five Production Package areas for every action', () => {
    render(<App initialRun={mockRun} forceMock />);
    expect(screen.getAllByText('SCRIPT')).toHaveLength(3);
    expect(screen.getAllByText('SHOT LIST')).toHaveLength(3);
    expect(screen.getAllByText('EDITING GUIDE')).toHaveLength(3);
    expect(screen.getAllByText('THUMBNAIL PLAN')).toHaveLength(3);
    expect(screen.getAllByText('PUBLISHING PACKAGE')).toHaveLength(3);
  });

  it('renders null follower data as 미확인 rather than zero', () => {
    const noFollowers: Run = {
      ...mockRun,
      result: { ...mockRun.result!, followers: null },
    };
    render(<App initialRun={noFollowers} forceMock />);
    expect(screen.getByText('ZIP pair가 없으면 팔로워 이력은 0이 아니라 미확인입니다.')).toBeInTheDocument();
    expect(screen.getAllByText('미확인').length).toBeGreaterThan(0);
  });

  it('shows partial and failure state without fabricating success', () => {
    const partial: Run = { ...mockRun, status: 'partial', stage: 'render', is_mock: false };
    const { unmount } = render(<App initialRun={partial} forceMock={false} />);
    expect(screen.getByText(/부분 완료 상태입니다/)).toBeInTheDocument();
    unmount();

    const failed: Run = {
      ...mockRun,
      status: 'failed',
      stage: 'analyze',
      is_mock: false,
      result: null,
      error: { code: 'PROVIDER_UNAVAILABLE', message: 'Nosana unavailable', retryable: true },
    };
    render(<App initialRun={failed} forceMock={false} />);
    expect(screen.getByText(/실행 실패: Nosana unavailable/)).toBeInTheDocument();
    expect(screen.queryByText('콘텐츠 전략')).not.toBeInTheDocument();
  });

  it('distinguishes a real synthetic run from mock execution', () => {
    const liveSynthetic: Run = {
      ...mockRun,
      is_mock: false,
      trace: mockRun.trace.map((trace) => ({ ...trace, mode: 'live' as const })),
    };
    render(<App initialRun={liveSynthetic} forceMock={false} />);
    expect(screen.queryByText(/fixture 기반 화면 개발 모드/)).not.toBeInTheDocument();
    expect(screen.getByText(/실제 실행 · evidence synthetic/)).toBeInTheDocument();
  });

  it('exposes ComfyUI | sangh handoff for children animation content', async () => {
    const user = userEvent.setup();
    render(<App initialRun={mockRun} forceMock />);
    await user.click(screen.getByLabelText(/어린이용 애니메이션 콘텐츠/));
    expect(screen.getAllByText('ComfyUI | sangh · 어린이 애니메이션 핸드오프')).toHaveLength(3);
    expect(screen.getAllByText(/cogvideox_5b_i2v_q4_rtx4060_minimal/)).toHaveLength(3);
  });
});
