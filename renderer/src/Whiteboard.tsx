import React from 'react';
import {AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

import {KineticText} from './components/KineticText';
import {SvgDrawer} from './components/SvgDrawer';
import type {RenderProps, SceneChoreography} from './types';
import {TRANSITION_FRAMES} from './types';

const VIEWPORT_W = 1920;
const VIEWPORT_H = 1080;
const SCENE_W = 1920;
const SCENE_H = 1080;

const msToFrames = (ms: number, fps: number): number => Math.max(1, Math.round((ms / 1000) * fps));

const toStaticAsset = (assetPath: string): string => {
  if (assetPath.startsWith('http')) return assetPath;
  const cleaned = assetPath.replace(/^\/+/, '');
  const withoutPublic = cleaned.startsWith('public/') ? cleaned.slice('public/'.length) : cleaned;
  return staticFile(withoutPublic);
};

// ── Timeline ──────────────────────────────────────────────────────────────────

function buildTimeline(scenes: SceneChoreography[], fps: number) {
  const sceneFrames = scenes.map(s => msToFrames(s.audio_duration_ms, fps));
  const startFrames: number[] = [];
  let cumulative = 0;
  for (const f of sceneFrames) {
    startFrames.push(cumulative);
    cumulative += f;
  }
  return {sceneFrames, startFrames};
}

// ── Camera ────────────────────────────────────────────────────────────────────
// cameraCenterX: world-x that should appear at the horizontal viewport centre.
// zoom: CSS scale applied to the canvas-world div.
// Transform: translate(tx, ty) scale(zoom) with transformOrigin "0 0"
//   tx = VIEWPORT_W/2 - cameraCenterX * zoom
//   ty = VIEWPORT_H/2 - (SCENE_H/2) * zoom
// This keeps (cameraCenterX, SCENE_H/2) pinned to viewport centre at any zoom.

function computeCamera(
  frame: number,
  scenes: SceneChoreography[],
  sceneFrames: number[],
  startFrames: number[],
): {cameraCenterX: number; cameraCenterY: number; zoom: number} {
  let idx = scenes.length - 1;
  for (let i = 0; i < startFrames.length; i++) {
    if (frame < startFrames[i] + sceneFrames[i]) {
      idx = i;
      break;
    }
  }

  const frameInScene = frame - startFrames[idx];
  const scene = scenes[idx];
  const sceneCenterX = scene.canvas_x + SCENE_W / 2;
  const sceneCenterY = scene.canvas_y + SCENE_H / 2;

  // ── Scene 0: no transition, start Ken-Burns immediately ───────────────────
  if (idx === 0) {
    const restProgress = sceneFrames[0] > 0 ? frameInScene / sceneFrames[0] : 0;
    const eio = Easing.inOut(Easing.quad);
    const zoom = interpolate(Math.min(1, restProgress), [0, 1], [1.0, 1.04], {
      easing: eio,
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    });
    return {cameraCenterX: sceneCenterX, cameraCenterY: sceneCenterY, zoom};
  }

  // ── Transition: first TRANSITION_FRAMES of scene N>0 ────────────────────
  // Phase 1 [0, 0.33]: zoom out  1.04→0.88, hold at prev scene centre
  // Phase 2 [0.33, 0.66]: pan prev→current at zoom 0.88
  // Phase 3 [0.66, 1.0]: zoom in 0.88→1.0,  hold at current scene centre
  if (frameInScene < TRANSITION_FRAMES) {
    const t = frameInScene / TRANSITION_FRAMES;
    const prevScene = scenes[idx - 1];
    const prevCenterX = prevScene.canvas_x + SCENE_W / 2;
    const prevCenterY = prevScene.canvas_y + SCENE_H / 2;

    const eio = Easing.inOut(Easing.quad);
    const opts = {easing: eio, extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};

    const zoom =
      t < 0.33
        ? interpolate(t, [0, 0.33], [1.04, 0.88], opts)
        : t < 0.66
          ? 0.88
          : interpolate(t, [0.66, 1.0], [0.88, 1.0], opts);

    const cameraCenterX =
      t < 0.33
        ? prevCenterX
        : t < 0.66
          ? interpolate(t, [0.33, 0.66], [prevCenterX, sceneCenterX], opts)
          : sceneCenterX;

    const cameraCenterY =
      t < 0.33
        ? prevCenterY
        : t < 0.66
          ? interpolate(t, [0.33, 0.66], [prevCenterY, sceneCenterY], opts)
          : sceneCenterY;

    return {cameraCenterX, cameraCenterY, zoom};
  }

  // ── Scene rest: slow Ken-Burns zoom 1.0 → 1.04 ───────────────────────────
  const restDuration = sceneFrames[idx] - TRANSITION_FRAMES;
  const restFrame = frameInScene - TRANSITION_FRAMES;
  const restProgress = restDuration > 0 ? restFrame / restDuration : 0;
  const eio = Easing.inOut(Easing.quad);
  const zoom = interpolate(Math.min(1, restProgress), [0, 1], [1.0, 1.04], {
    easing: eio,
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return {cameraCenterX: sceneCenterX, cameraCenterY: sceneCenterY, zoom};
}

// ── Root composition ──────────────────────────────────────────────────────────

export const Whiteboard: React.FC<RenderProps> = ({fps, scenes}) => {
  const frame = useCurrentFrame();
  const {fps: configFps} = useVideoConfig();
  const validFps = fps || configFps || 30;

  if (!scenes.length) {
    return (
      <AbsoluteFill
        style={{
          background: '#fdfdfd',
          fontFamily: 'sans-serif',
          color: '#13294b',
          justifyContent: 'center',
          alignItems: 'center',
          fontSize: 48,
        }}
      >
        Waiting for pipeline...
      </AbsoluteFill>
    );
  }

  const {sceneFrames, startFrames} = buildTimeline(scenes, validFps);
  const {cameraCenterX, cameraCenterY, zoom} = computeCamera(frame, scenes, sceneFrames, startFrames);

  const tx = VIEWPORT_W / 2 - cameraCenterX * zoom;
  const ty = VIEWPORT_H / 2 - cameraCenterY * zoom;

  const worldWidth = Math.max(...scenes.map(s => s.canvas_x + SCENE_W));
  const worldHeight = Math.max(...scenes.map(s => s.canvas_y + SCENE_H));

  return (
    <AbsoluteFill style={{background: '#fdfdfd', overflow: 'hidden'}}>
      {/* Load Caveat font */}
      <link
        href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap"
        rel="stylesheet"
      />
      {/* Dot-grid background — fixed to viewport, not part of canvas world */}
      <AbsoluteFill
        style={{
          backgroundImage: 'radial-gradient(#d8d8d8 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          opacity: 0.7,
          pointerEvents: 'none',
        }}
      />

      {/* Canvas world — absolute positioning based on backend coords */}
      <div
        style={{
          position: 'absolute',
          width: worldWidth,
          height: worldHeight,
          transform: `translate(${tx}px, ${ty}px) scale(${zoom})`,
          transformOrigin: '0 0',
        }}
      >
        {scenes.map((scene, i) => {
          const drawDurationFrames = msToFrames(scene.draw_duration_ms, validFps);
          // Extend last non-final scene by TRANSITION_FRAMES so it stays visible
          // while the camera pans to the next scene.
          const visibleFrames = sceneFrames[i] + (i < scenes.length - 1 ? TRANSITION_FRAMES : 0);

          return (
            <Sequence
              key={scene.scene_id}
              from={startFrames[i]}
              durationInFrames={visibleFrames}
              layout="none"
            >
              <div
                style={{
                  position: 'absolute',
                  left: scene.canvas_x,
                  top: scene.canvas_y,
                  width: SCENE_W,
                  height: SCENE_H,
                  overflow: 'hidden',
                }}
              >
                {/* Top 35% — kinetic text, left-aligned */}
                <div style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '35%'}}>
                  <KineticText
                    narration={scene.on_screen_text}
                    kineticWords={scene.kinetic_words || []}
                    sceneDurationFrames={sceneFrames[i]}
                  />
                </div>
                {/* Bottom 65% — SVG illustration(s) */}
                <div style={{position: 'absolute', left: 0, top: '35%', width: '100%', height: '65%'}}>
                  {scene.svg_content_secondary ? (
                    // ── Dual layout: primary (left 55%) + secondary (right 45%) ──
                    <>
                      {/* Primary SVG — left 55%, starts immediately */}
                      <div style={{
                        position: 'absolute',
                        left: 0,
                        top: 0,
                        width: '55%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <SvgDrawer
                          svgContent={scene.svg_content}
                          drawDurationFrames={drawDurationFrames}
                          sceneDurationFrames={sceneFrames[i]}
                        />
                      </div>
                      {/* Secondary SVG — right 45%, starts 20 frames later */}
                      <div style={{
                        position: 'absolute',
                        right: 0,
                        top: 0,
                        width: '45%',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}>
                        <Sequence from={20} layout="none">
                          <SvgDrawer
                            svgContent={scene.svg_content_secondary}
                            drawDurationFrames={drawDurationFrames}
                            sceneDurationFrames={Math.max(1, sceneFrames[i] - 20)}
                          />
                        </Sequence>
                      </div>
                    </>
                  ) : (
                    // ── Single layout: primary centered at 480px wide ──
                    <SvgDrawer
                      svgContent={scene.svg_content}
                      drawDurationFrames={drawDurationFrames}
                      sceneDurationFrames={sceneFrames[i]}
                    />
                  )}
                </div>
              </div>
            </Sequence>
          );
        })}
      </div>

      {/* Audio — outside canvas world so transforms don't affect it */}
      {scenes.map((scene, i) => (
        <Sequence
          key={`audio-${scene.scene_id}`}
          from={startFrames[i]}
          durationInFrames={sceneFrames[i]}
          layout="none"
        >
          <Audio src={toStaticAsset(scene.audio_path)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

