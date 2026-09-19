import type { Action } from '../types';

const DEFAULT_BASE = '/comfyui';
const DEFAULT_PUBLIC_URL = 'http://127.0.0.1:8188';

export interface ComfyStatus {
  ok: boolean;
  label: string;
  detail: string;
}

export interface ComfyPromptBundle {
  workflow: string;
  characterPrompt: string;
  scenePrompts: string[];
  thumbnailPrompt: string;
  safetyNotes: string[];
}

export function comfyBase(): string {
  return import.meta.env.VITE_COMFYUI_BASE || DEFAULT_BASE;
}

export function comfyPublicUrl(): string {
  return import.meta.env.VITE_COMFYUI_PUBLIC_URL || DEFAULT_PUBLIC_URL;
}

export async function checkComfyUi(signal?: AbortSignal): Promise<ComfyStatus> {
  try {
    const response = await fetch(`${comfyBase()}/system_stats`, { signal });
    if (!response.ok) {
      return {
        ok: false,
        label: 'ComfyUI | sangh 연결 실패',
        detail: `HTTP ${response.status}`,
      };
    }
    const data = (await response.json()) as { system?: { comfyui_version?: string } };
    return {
      ok: true,
      label: 'ComfyUI | sangh 연결됨',
      detail: data.system?.comfyui_version
        ? `ComfyUI ${data.system.comfyui_version}`
        : '127.0.0.1:8188 로컬 인스턴스',
    };
  } catch {
    return {
      ok: false,
      label: 'ComfyUI | sangh 연결 안 됨',
      detail: '로컬 ComfyUI(127.0.0.1:8188)를 실행한 뒤 다시 확인하세요.',
    };
  }
}

export function buildChildrenAnimationBundle(action: Action): ComfyPromptBundle {
  const characterPrompt = [
    'child-friendly animated short, warm and educational, recurring original character design',
    'clear facial expressions, simple readable silhouette, soft lighting, vivid but comfortable colors',
    'consistent costume and proportions across scenes, no logos, no copyrighted characters',
    `story intent: ${action.title}`,
  ].join(', ');

  const scenePrompts = action.production_package.shot_list.map((shot) =>
    [
      `Scene ${shot.order}, about ${shot.duration_sec} seconds`,
      characterPrompt,
      `visual: ${shot.visual}`,
      `narrative beat: ${shot.narration}`,
      'camera movement should be gentle and easy for children to follow',
      'keep on-screen text out of the generated image; add subtitles in editing',
    ].join(' | '),
  );

  const thumbnailPrompt = [
    characterPrompt,
    `thumbnail concept: ${action.production_package.thumbnail_plan.concept}`,
    `composition: ${action.production_package.thumbnail_plan.composition}`,
    `reference generation direction: ${action.production_package.thumbnail_plan.generation_prompt}`,
    'leave clean negative space for the exact Korean thumbnail text to be added later in editing',
  ].join(' | ');

  return {
    workflow: 'cogvideox_5b_i2v_q4_rtx4060_minimal (ComfyUI | sangh)',
    characterPrompt,
    scenePrompts,
    thumbnailPrompt,
    safetyNotes: [
      '어린이에게 불필요하게 무섭거나 위험한 행동을 사실적으로 묘사하지 않습니다.',
      '실존 아동의 얼굴·개인정보를 프롬프트에 넣지 않습니다.',
      '기존 유명 캐릭터를 복제하지 않고 오리지널 캐릭터를 사용합니다.',
      'ComfyUI 생성물은 초안 영상/이미지이며 게시 전 사람이 장면·자막·음원을 검수합니다.',
    ],
  };
}
