import React, {useMemo, useRef, useEffect, useState} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';

type SvgDrawerProps = {
  svgContent: string;
  drawDurationFrames: number;
  sceneDurationFrames: number;
};

type ParsedAttr = Record<string, string>;
type ParsedNode = {
  kind: 'path' | 'line' | 'polyline' | 'polygon' | 'rect' | 'circle' | 'ellipse';
  attrs: ParsedAttr;
};

const parseAttrs = (attrStr: string): ParsedAttr => {
  const result: ParsedAttr = {};
  const re = /([\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(attrStr)) !== null) {
    result[m[1]] = m[2] ?? m[3] ?? '';
  }
  return result;
};

const parseSvgNodes = (markup: string): ParsedNode[] => {
  const nodes: ParsedNode[] = [];
  const shapeRe = /<(path|line|polyline|polygon|rect|circle|ellipse)\b([^>]*?)\s*\/?>/gi;
  let m: RegExpExecArray | null;
  while ((m = shapeRe.exec(markup)) !== null) {
    const tag = m[1].toLowerCase() as ParsedNode['kind'];
    const attrs = parseAttrs(m[2]);
    nodes.push({kind: tag, attrs});
  }
  return nodes;
};

const extractViewBox = (markup: string): string => {
  const m = markup.match(/viewBox\s*=\s*["']([^"']*)["']/i);
  return m ? m[1] : '0 0 400 300';
};

const RoughElement: React.FC<{
  node: ParsedNode;
  progress: number;
  index: number;
}> = ({node, progress, index}) => {
  const [roughPath, setRoughPath] = useState<string>('');

  useEffect(() => {
    const rc = rough.svg(document.createElementNS('http://www.w3.org/2000/svg', 'svg'));
    let generator;
    
    // Determine color: priority to stroke, then fill if it's not "none"
    const color = node.attrs.stroke || (node.attrs.fill !== 'none' ? node.attrs.fill : '#1a1a1a');

    const options = {
      stroke: color,
      strokeWidth: 2,
      roughness: 1.2,
      bowing: 1,
      seed: index + 1,
    };

    if (node.kind === 'path') {
      generator = rc.path(node.attrs.d, options);
    } else if (node.kind === 'circle') {
      generator = rc.circle(Number(node.attrs.cx), Number(node.attrs.cy), Number(node.attrs.r) * 2, options);
    } else if (node.kind === 'rect') {
      generator = rc.rectangle(Number(node.attrs.x), Number(node.attrs.y), Number(node.attrs.width), Number(node.attrs.height), options);
    } else if (node.kind === 'line') {
      generator = rc.line(Number(node.attrs.x1), Number(node.attrs.y1), Number(node.attrs.x2), Number(node.attrs.y2), options);
    } else if (node.kind === 'polyline' || node.kind === 'polygon') {
      const points = node.attrs.points.split(/[\s,]+/).map(Number).reduce((acc: any, val, i) => {
        if (i % 2 === 0) acc.push([val]);
        else acc[acc.length - 1].push(val);
        return acc;
      }, []);
      generator = node.kind === 'polygon' ? rc.polygon(points, options) : rc.linearPath(points, options);
    } else {
      return;
    }

    const paths = generator.querySelectorAll('path');
    let combinedPath = '';
    paths.forEach(p => {
      combinedPath += p.getAttribute('d') + ' ';
    });
    setRoughPath(combinedPath);
  }, [node, index]);

  if (!roughPath || progress <= 0) return null;

  return (
    <path
      d={roughPath}
      fill="none"
      stroke={node.attrs.stroke || '#1a1a1a'}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      pathLength={1}
      style={{
        strokeDasharray: 1,
        strokeDashoffset: 1 - progress,
        opacity: Math.min(1, progress * 2),
      }}
    />
  );
};

export const SvgDrawer: React.FC<SvgDrawerProps> = ({svgContent, drawDurationFrames, sceneDurationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Hooks must always be called unconditionally (React rules of hooks).
  // Pass empty string default so these are safe even for text-only scenes.
  const allNodes = useMemo(() => parseSvgNodes(svgContent || ''), [svgContent]);
  const viewBox = useMemo(() => extractViewBox(svgContent || ''), [svgContent]);

  const entranceSpring = spring({fps, frame, config: {damping: 100, stiffness: 50}});
  const sceneOpacity = interpolate(
    frame,
    [0, 10, Math.max(11, sceneDurationFrames - 15), sceneDurationFrames],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
  );

  // Text-only scene — no SVG asset. Render a clean blank canvas.
  if (!svgContent || svgContent.trim() === '') {
    return (
      <AbsoluteFill style={{
        backgroundColor: '#fdfdfd',
        backgroundImage: 'radial-gradient(#e5e5e5 1px, transparent 1px)',
        backgroundSize: '50px 50px',
        opacity: sceneOpacity,
      }} />
    );
  }

  return (
    <AbsoluteFill style={{
      backgroundColor: '#fdfdfd',
      backgroundImage: 'radial-gradient(#e5e5e5 1px, transparent 1px)',
      backgroundSize: '50px 50px',
      opacity: sceneOpacity,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        width: '60%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: `scale(${0.9 + entranceSpring * 0.1})`,
      }}>
        <svg viewBox={viewBox} xmlns="http://www.w3.org/2000/svg"
          style={{width: '100%', height: 'auto', overflow: 'visible', display: 'block'}}>
          {allNodes.map((node, i) => {
            const elementDelay = (i / Math.max(1, allNodes.length)) * drawDurationFrames * 0.7;
            const elementProgress = interpolate(
              frame - elementDelay,
              [0, drawDurationFrames * 0.3],
              [0, 1],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}
            );
            return (
              <RoughElement
                key={`${i}-${node.kind}`}
                node={node}
                index={i}
                progress={elementProgress}
              />
            );
          })}
        </svg>
      </div>
    </AbsoluteFill>
  );
};