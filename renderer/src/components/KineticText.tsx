import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

type KineticTextProps = {
  narration: string;
  kineticWords?: string[];
  sceneDurationFrames: number;
};

const cleanWord = (word: string) => word.toLowerCase().replace(/[^\w]/g, '');

export const KineticText: React.FC<KineticTextProps> = ({
  narration,
  kineticWords = [],
  sceneDurationFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const words = narration.split(' ');
  if (frame < 0) return null;

  const kineticSet = new Set((kineticWords || []).map(cleanWord));

  return (
    <div
      style={{
        fontFamily: '"Caveat", cursive',
        fontSize: '72px',
        color: '#1a1a1a',
        lineHeight: '1.15',
        textAlign: 'left',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'flex-start',
        alignItems: 'flex-start',
        alignContent: 'flex-start',
        gap: '14px',
        width: '100%',
        height: '100%',
        padding: '40px 80px',
        boxSizing: 'border-box',
      }}
    >
      {words.map((word, i) => {
        const isKinetic = kineticSet.has(cleanWord(word));
        // Stamp all words within ~1 second regardless of scene length
        const totalRevealFrames = Math.min(30, sceneDurationFrames * 0.1);
        const wordDelay = (i / Math.max(1, words.length - 1)) * totalRevealFrames;

        const opacity = interpolate(
          frame - wordDelay,
          [0, 6],
          [0, 1],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );

        const springVal = spring({
          fps,
          frame: frame - wordDelay,
          config: {
            damping: 12,
            stiffness: 100,
          },
        });

        const scale = isKinetic
          ? interpolate(springVal, [0, 1], [0.5, 1.4])
          : interpolate(springVal, [0, 1], [0.8, 1]);

        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity,
              transform: `scale(${scale})`,
              fontWeight: isKinetic ? 'bold' : 'normal',
              color: isKinetic ? '#2563eb' : '#1a1a1a',
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
