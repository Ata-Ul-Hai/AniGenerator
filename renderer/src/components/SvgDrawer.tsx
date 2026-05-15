import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

type SvgDrawerProps = {
  svgContent: string;
  drawDurationFrames: number;
  sceneDurationFrames: number;
};

const extractViewBox = (markup: string): string => {
  const m = markup.match(/viewBox\s*=\s*["']([^"']*)["']/i);
  return m ? m[1] : '0 0 800 600';
};

// Extract inner SVG content (everything between the outer <svg> tags)
const extractInnerSvg = (markup: string): string => {
  const start = markup.indexOf('>');
  if (start === -1) return '';
  const end = markup.lastIndexOf('</svg>');
  if (end <= start) return markup.slice(start + 1);
  return markup.slice(start + 1, end);
};

// Detect colored illustration vs stroke-only icon
const detectIsIllustration = (markup: string): boolean =>
  /fill\s*=\s*["']#[0-9a-fA-F]{3,6}["']/.test(markup) ||
  markup.includes('data-name=');

export const SvgDrawer: React.FC<SvgDrawerProps> = ({svgContent, drawDurationFrames, sceneDurationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const viewBox = useMemo(() => extractViewBox(svgContent || ''), [svgContent]);
  const innerSvg = useMemo(() => extractInnerSvg(svgContent || ''), [svgContent]);
  const isIllustration = useMemo(() => detectIsIllustration(svgContent || ''), [svgContent]);
  const targetWidth = isIllustration ? 700 : 650;

  const entranceSpring = spring({fps, frame, config: {damping: 100, stiffness: 50}});

  // Container fade-in (0→10f) and fade-out before scene end
  const sceneOpacity = interpolate(
    frame,
    [0, 10, Math.max(11, sceneDurationFrames - 15), sceneDurationFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Left-to-right wipe reveals the SVG over drawDurationFrames
  const drawProgress = interpolate(
    frame,
    [0, Math.max(1, drawDurationFrames)],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  if (!svgContent || svgContent.trim() === '') {
    return <AbsoluteFill style={{opacity: sceneOpacity}} />;
  }

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: targetWidth,
          transform: `scale(${0.9 + entranceSpring * 0.1})`,
          flexShrink: 0,
          clipPath: `inset(0 ${(1 - drawProgress) * 100}% 0 0 round 4px)`,
        }}
      >
        <svg
          viewBox={viewBox}
          xmlns="http://www.w3.org/2000/svg"
          style={{width: '100%', height: 'auto', overflow: 'visible', display: 'block'}}
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{__html: innerSvg}}
        />
      </div>
    </AbsoluteFill>
  );
};
