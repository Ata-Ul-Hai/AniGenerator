import React from 'react';
import {AbsoluteFill, Audio, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

import {Subtitles} from './components/Subtitles';
import {SvgDrawer} from './components/SvgDrawer';
import type {RenderProps, SceneChoreography} from './types';

const TRANSITION_MS = 450;

const msToFrames = (valueMs: number, fps: number): number => Math.max(1, Math.round((valueMs / 1000) * fps));

const toStaticAsset = (assetPath: string): string => {
  const cleaned = assetPath.replace(/^\/+/, '');
  const withoutPublic = cleaned.startsWith('public/') ? cleaned.slice('public/'.length) : cleaned;
  return staticFile(withoutPublic);
};

const SceneLayer: React.FC<{
  scene: SceneChoreography;
  sceneDurationFrames: number;
  drawDurationFrames: number;
}> = ({scene, sceneDurationFrames, drawDurationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const reveal = spring({
    fps,
    frame,
    config: {
      damping: 220,
      stiffness: 90,
      mass: 0.7,
    },
  });

  return (
    <AbsoluteFill
      style={{
        transform: `translateY(${(1 - reveal) * 30}px) scale(${0.985 + reveal * 0.015})`,
      }}
    >
      <SvgDrawer
        svgContent={scene.svg_content}
        drawDurationFrames={drawDurationFrames}
        sceneDurationFrames={sceneDurationFrames}
      />
      <Subtitles narration={scene.narration} sceneDurationFrames={sceneDurationFrames} />
      <Audio src={toStaticAsset(scene.audio_path)} />
    </AbsoluteFill>
  );
};

export const Whiteboard: React.FC<RenderProps> = ({fps, scenes}) => {
  const validFps = fps || 30;
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  if (!scenes.length) {
    return (
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(circle at 15% 20%, rgba(255,255,255,0.7), rgba(228,234,245,0.4) 40%, rgba(181,198,223,0.45)), linear-gradient(120deg, #f6ead2, #d5e4f7 45%, #bfd0e9)',
          fontFamily: '"Didot", "Bodoni MT", serif',
          color: '#13294b',
          justifyContent: 'center',
          alignItems: 'center',
          letterSpacing: '0.04em',
          fontSize: 68,
        }}
      >
        Waiting for render_props scenes...
      </AbsoluteFill>
    );
  }

  let cursor = 0;

  return (
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(circle at 8% 14%, rgba(255, 251, 240, 0.92), rgba(245, 224, 179, 0.4) 40%, rgba(199, 223, 244, 0.58) 70%), linear-gradient(145deg, #f4dfb5, #e8f2fb 46%, #cadcf2)',
        overflow: 'hidden',
      }}
    >
      <AbsoluteFill
        style={{
          backgroundImage:
            'linear-gradient(rgba(26,52,88,0.055) 1px, transparent 1px), linear-gradient(90deg, rgba(26,52,88,0.055) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          mixBlendMode: 'multiply',
          pointerEvents: 'none',
        }}
      />
      <AbsoluteFill
        style={{
          pointerEvents: 'none',
          background:
            'radial-gradient(circle at 92% 88%, rgba(12, 36, 72, 0.12), transparent 24%), radial-gradient(circle at 12% 88%, rgba(161, 66, 38, 0.17), transparent 29%)',
        }}
      />

      {scenes.map((scene) => {
        const sceneFrames = msToFrames(scene.audio_duration_ms + TRANSITION_MS, validFps);
        const drawDurationFrames = msToFrames(scene.draw_duration_ms, validFps);
        const sequenceFrom = cursor;
        cursor += sceneFrames;

        return (
          <Sequence key={scene.scene_id} from={sequenceFrom} durationInFrames={sceneFrames}>
            <SceneLayer
              scene={scene}
              drawDurationFrames={drawDurationFrames}
              sceneDurationFrames={sceneFrames}
            />
          </Sequence>
        );
      })}

      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            margin: '0 60px 40px',
            height: 8,
            borderRadius: 999,
            background: 'rgba(15, 35, 58, 0.16)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${(frame / Math.max(1, durationInFrames)) * 100}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #7b2e19, #123c80)',
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
