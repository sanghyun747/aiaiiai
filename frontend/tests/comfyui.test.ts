import { describe, expect, it } from 'vitest';
import { buildChildrenAnimationBundle } from '../src/lib/comfyui';
import { mockRun } from '../src/mock/runSample';

describe('ComfyUI production handoff', () => {
  it('converts every shot into a child-safe scene prompt without claiming a render', () => {
    const action = mockRun.result!.actions[0];
    const bundle = buildChildrenAnimationBundle(action);
    expect(bundle.scenePrompts).toHaveLength(action.production_package.shot_list.length);
    expect(bundle.characterPrompt).toContain('child-friendly animated short');
    expect(bundle.characterPrompt).toContain('no copyrighted characters');
    expect(bundle.workflow).toContain('cogvideox_5b_i2v_q4_rtx4060_minimal');
    expect(bundle.safetyNotes.some((note) => note.includes('실존 아동'))).toBe(true);
  });
});
