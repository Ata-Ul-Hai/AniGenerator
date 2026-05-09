import React from 'react';
import {AbsoluteFill, Audio, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {TransitionSeries, springTiming} from '@remotion/transitions';
import {slide} from '@remotion/transitions/slide';

import {Subtitles} from './components/Subtitles';
import {SvgDrawer} from './components/SvgDrawer';
import {LottieDrawer} from './components/LottieDrawer';
import type {RenderProps, SceneChoreography} from './types';
import {TRANSITION_MS} from './types';

const msToFrames = (valueMs: number, fps: number): number => Math.max(1, Math.round((valueMs / 1000) * fps));

const toStaticAsset = (assetPath: string): string => {
  if (assetPath.startsWith('http')) return assetPath;
  const cleaned = assetPath.replace(/^\/+/, '');
  const withoutPublic = cleaned.startsWith('public/') ? cleaned.slice('public/'.length) : cleaned;
  return staticFile(withoutPublic);
};

const SceneLayer: React.FC<{
  scene: SceneChoreography;
  sceneDurationFrames: number;
  drawDurationFrames: number;
}> = ({scene, sceneDurationFrames, drawDurationFrames}) => {
  const isLottie = scene.svg_path.startsWith('lottie://');

  return (
    <AbsoluteFill>
      {isLottie ? (
        <LottieDrawer
          lottieJson={scene.svg_content}
          drawDurationFrames={drawDurationFrames}
          sceneDurationFrames={sceneDurationFrames}
        />
      ) : (
        <SvgDrawer
          svgContent={scene.svg_content}
          drawDurationFrames={drawDurationFrames}
          sceneDurationFrames={sceneDurationFrames}
        />
      )}
      <Subtitles narration={scene.narration} sceneDurationFrames={sceneDurationFrames} />
      <Audio src={toStaticAsset(scene.audio_path)} />
    </AbsoluteFill>
  );
};

export const Whiteboard: React.FC<RenderProps> = ({fps, scenes}) => {
  const validFps = fps || 30;

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

  return (
    <AbsoluteFill
      style={{
        background: '#fdfdfd', // Base Paper
        overflow: 'hidden',
      }}
    >
      {/* Universal Grid Pattern */}
      <AbsoluteFill
        style={{
          backgroundImage: 'radial-gradient(#e5e5e5 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          opacity: 0.8,
          pointerEvents: 'none',
        }}
      />

      <TransitionSeries>
        {scenes.map((scene, i) => {
          const sceneFrames = msToFrames(scene.audio_duration_ms + TRANSITION_MS, validFps);
          const drawDurationFrames = msToFrames(scene.draw_duration_ms, validFps);

          return (
            <React.Fragment key={scene.scene_id}>
              <TransitionSeries.Sequence durationInFrames={sceneFrames}>
                <SceneLayer
                  scene={scene}
                  drawDurationFrames={drawDurationFrames}
                  sceneDurationFrames={sceneFrames}
                />
              </TransitionSeries.Sequence>
              {i < scenes.length - 1 && (
                <TransitionSeries.Transition
                  presentation={slide({direction: 'from-right'})}
                  timing={springTiming({
                    config: {damping: 200, stiffness: 80},
                    durationInFrames: 18,
                  })}
                />
              )}
            </React.Fragment>
          );
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
