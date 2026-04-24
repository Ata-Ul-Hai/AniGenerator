import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

type SubtitlesProps = {
  narration: string;
  sceneDurationFrames: number;
};

export const Subtitles: React.FC<SubtitlesProps> = ({narration, sceneDurationFrames}) => {
  const frame = useCurrentFrame();
  const fadeIn = interpolate(frame, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  const fadeOut = interpolate(
    frame,
    [Math.max(0, sceneDurationFrames - 12), sceneDurationFrames],
    [1, 0],
    {extrapolateLeft: 'clamp'},
  );

  return (
    <div
      style={{
        position: 'absolute',
        left: 80,
        right: 80,
        bottom: 70,
        opacity: fadeIn * fadeOut,
        transform: `translateY(${(1 - fadeIn) * 12}px)`,
        zIndex: 20,
      }}
    >
      <div
        style={{
          background: 'rgba(15, 20, 30, 0.72)',
          border: '1px solid rgba(255,255,255,0.35)',
          borderRadius: 26,
          padding: '24px 30px',
          color: '#f7f4ed',
          fontFamily: '"Inter", "Segoe UI", sans-serif',
          fontSize: 38,
          lineHeight: 1.28,
          boxShadow: '0 24px 48px rgba(8, 13, 20, 0.35)',
        }}
      >
        {narration}
      </div>
    </div>
  );
};
