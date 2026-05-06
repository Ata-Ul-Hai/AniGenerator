import React, {useMemo, useRef, useEffect, useState} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import rough from 'roughjs';

type SvgDrawerProps = {
  svgContent: string;
  drawDurationFrames: number;
  sceneDurationFrames: number;
};

type ParsedAttr = Record<string, string>;
type PathNode = {kind: 'path' | 'line' | 'polyline' | 'polygon'; attrs: ParsedAttr};
type FillNode = {kind: 'rect' | 'circle' | 'ellipse'; attrs: ParsedAttr};
type ParsedNode = PathNode | FillNode;

const parseAttrs = (attrStr: string): ParsedAttr => {
  const result: ParsedAttr = {};
  const re = /([\w-]+)\s*=\s*(? ("([^"]*)"|'([^']*)')/g;
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
    nodes.push({kind: tag, attrs} as ParsedNode);
  }
  return nodes;
};

const extractViewBox = (markup: string): string => {
  const m = markup.match(/viewBox\s*=\s*["']([^"']*)["']/i);
  return m ? m[1] : '0 0 400 400';
};

const RoughElement: React.FC<{
  node: ParsedNode;
  progress: number;
  index: number;
}> = ({node, progress, index}) => {
  const svgRef = useRef<SVGGElement>(null);
  const [roughPath, setRoughPath] = useState<string>('');

  useEffect(() => {
    const rc = rough.svg(document.createElementNS('http://www.w3.org/2000/svg', 'svg'));
    let generator;
    
    const options = {
      stroke: node.attrs.stroke || '#000',
      strokeWidth: 2,
      roughness: 1.5,
      bowing: 1,
      seed: index + 1, // Stable seed for this element
    };

    if (node.kind === 'path') {
      generator = rc.path(node.attrs.d, options);
    } else if (node.kind === 'circle') {
      generator = rc.circle(Number(node.attrs.cx), Number(node.attrs.cy), Number(node.attrs.r) * 2, options);
    } else if (node.kind === 'rect') {
      generator = rc.rectangle(Number(node.attrs.x), Number(node.attrs.y), Number(node.attrs.width), Number(node.attrs.height), options);
    } else {
      // Fallback or other shapes
      return;
    }

    // Extract the path data from the rough generated element
    // Rough.js returns an SVGGElement containing multiple paths
    const paths = generator.querySelectorAll('path');
    let combinedPath = '';
    paths.forEach(p => {
      combinedPath += p.getAttribute('d') + ' ';
    });
    setRoughPath(combinedPath);
  }, [node, index]);

  if (!roughPath) return null;

  return (
    <path
      d={roughPath}
      fill="none"
      stroke={node.attrs.stroke || '#000'}
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      pathLength={1}
      style={{
        strokeDasharray: 1,
        strokeDashoffset: 1 - progress,
      }}
    />
  );
};

export const SvgDrawer: React.FC<SvgDrawerProps> = ({svgContent, drawDurationFrames, sceneDurationFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const allNodes = useMemo(() => parseSvgNodes(svgContent || ''), [svgContent]);
  const viewBox = useMemo(() => extractViewBox(svgContent || ''), [svgContent]);

  const entranceSpring = spring({fps, frame, config: {damping: 100, stiffness: 50}});
  const sceneOpacity = interpolate(frame,
    [0, 10, Math.max(11, sceneDurationFrames - 15), sceneDurationFrames],
    [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{
      backgroundColor: '#fdfdfd', // Paper color
      backgroundImage: 'radial-gradient(#e5e5e5 1px, transparent 1px)',
      backgroundSize: '40px 40px', // Grid look
      opacity: sceneOpacity,
    }}>
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transform: `scale(${0.95 + entranceSpring * 0.05})`,
      }}>
        <svg viewBox={viewBox} xmlns="http://www.w3.org/2000/svg"
          style={{width: '80%', height: '80%', overflow: 'visible'}}>
          {allNodes.map((node, i) => {
            const elementDelay = (i / allNodes.length) * drawDurationFrames * 0.5;
            const elementSpring = spring({
              fps,
              frame: Math.max(0, frame - elementDelay),
              config: {damping: 15, stiffness: 100},
            });
            return (
              <RoughElement 
                key={`${i}-${node.kind}`} 
                node={node} 
                index={i}
                progress={Math.min(1, elementSpring)} 
              />
            );
          })}
        </svg>
      </div>
    </AbsoluteFill>
  );
};