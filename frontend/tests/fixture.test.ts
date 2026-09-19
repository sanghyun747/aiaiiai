import { describe, expect, it } from 'vitest';
import { mockRun, parseRunFixture } from '../src/mock/runSample';

describe('typed fixture', () => {
  it('parses contract 1.1.0 fixture and preserves success invariants', () => {
    expect(mockRun.contract_version).toBe('1.1.0');
    expect(mockRun.is_mock).toBe(true);
    expect(mockRun.result?.actions).toHaveLength(3);
    expect(mockRun.result?.actions.some((action) => action.strategy_mode === 'safe_bet')).toBe(true);
    const growth = mockRun.result?.actions.filter((action) => action.strategy_mode === 'growth_experiment') ?? [];
    expect(growth.length).toBeGreaterThan(0);
    expect(growth.every((action) => Boolean(action.weakness_target))).toBe(true);
  });

  it('rejects a succeeded fixture with fewer than three actions', () => {
    const broken = structuredClone(mockRun) as unknown as Record<string, unknown>;
    const result = broken.result as { actions: unknown[] };
    result.actions = result.actions.slice(0, 2);
    expect(() => parseRunFixture(broken)).toThrow(/exactly three actions/);
  });
});
