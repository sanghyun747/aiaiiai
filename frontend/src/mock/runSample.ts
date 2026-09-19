import rawFixture from '../../../fixtures/run-sample.json';
import type { Run } from '../types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function parseRunFixture(value: unknown): Run {
  if (!isRecord(value)) throw new Error('Run fixture must be an object.');
  if (value.contract_version !== '1.1.0') throw new Error('Unexpected fixture contract version.');
  if (typeof value.run_id !== 'string') throw new Error('Fixture run_id is missing.');
  if (!['queued', 'running', 'succeeded', 'partial', 'failed'].includes(String(value.status))) {
    throw new Error('Fixture status is invalid.');
  }
  if (value.status === 'succeeded') {
    if (!isRecord(value.result) || !Array.isArray(value.result.actions)) {
      throw new Error('Succeeded fixture requires result.actions.');
    }
    if (value.result.actions.length !== 3) {
      throw new Error('Succeeded fixture must contain exactly three actions.');
    }
    const modes = value.result.actions
      .filter(isRecord)
      .map((action) => String(action.strategy_mode));
    if (!modes.includes('safe_bet') || !modes.includes('growth_experiment')) {
      throw new Error('Succeeded fixture requires SAFE BET and GROWTH EXPERIMENT.');
    }
    const growth = value.result.actions.filter(
      (action) => isRecord(action) && action.strategy_mode === 'growth_experiment',
    );
    if (growth.some((action) => typeof action.weakness_target !== 'string' || !action.weakness_target)) {
      throw new Error('Growth experiments require weakness_target.');
    }
  }
  return value as unknown as Run;
}

export const mockRun = parseRunFixture(rawFixture);

export async function runMock(
  onUpdate?: (run: Run) => void,
): Promise<Run> {
  await Promise.resolve();
  onUpdate?.(mockRun);
  return mockRun;
}
