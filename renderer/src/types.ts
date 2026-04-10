export type SceneChoreography = {
  scene_id: number;
  narration: string;
  svg_markup: string;
  metaphor_hint: string;
  audio_path: string;
  svg_path: string;
  svg_content: string;
  audio_duration_ms: number;
  draw_start_ms: number;
  draw_duration_ms: number;
  hold_ms: number;
};

export type RenderProps = {
  fps: number;
  width: number;
  height: number;
  scenes: SceneChoreography[];
};

/** Gap between scenes for transition animation (ms). Shared between Root and Whiteboard. */
export const TRANSITION_MS = 450;
