import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

type SvgDrawerProps = {
  svgContent: string;
  drawDurationFrames: number;
  sceneDurationFrames: number;
};

type ParsedAttr = Record<string, string>;
type PathNode = {kind: 'path' | 'line' | 'polyline' | 'polygon'; attrs: ParsedAttr};
type FillNode = {kind: 'rect' | 'circle' | 'ellipse'; attrs: ParsedAttr};
type TextNode = {kind: 'text'; attrs: ParsedAttr; content: string};
type ParsedNode = PathNode | FillNode | TextNode;

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

  // Parse self-closing and open shape tags
  const shapeRe = /<(path|line|polyline|polygon|rect|circle|ellipse)\b([^>]*?)\s*\/?>/gi;
  let m: RegExpExecArray | null;
  while ((m = shapeRe.exec(markup)) !== null) {
    const tag = m[1].toLowerCase() as ParsedNode['kind'];
    const attrs = parseAttrs(m[2]);
    nodes.push({kind: tag as PathNode['kind'] | FillNode['kind'], attrs} as PathNode | FillNode);
  }

  // Parse text elements with content
  const textRe = /<text\b([^>]*)>([\s\S]*?)<\/text>/gi;
  while ((m = textRe.exec(markup)) !== null) {
    nodes.push({kind: 'text', attrs: parseAttrs(m[1]), content: m[2].trim()});
  }

  return nodes;
};

const extractViewBox = (markup: string): string => {
  const m = markup.match(/viewBox\s*=\s*["']([^"']*)["']/i);
  return m ? m[1] : '0 0 400 300';
};

const elementProgress = (global: number, index: number, total: number): number => {
  if (total <= 1) return global;
  const start = index / total;
  const end = (index + 1) / total;
  return Math.max(0, Math.min(1, (global - start) / Math.max(0.001, end - start)));
};

type AnimatedPathProps = {node: PathNode; drawProgress: number; index: number; total: number};
const AnimatedPath: React.FC<AnimatedPathProps> = ({node, drawProgress, index, total}) => {
  const progress = elementProgress(drawProgress, index, total);
  const {stroke = '#1a1a1a', 'stroke-width': sw = '3', 'stroke-linecap': slc = 'round',
    'stroke-linejoin': slj = 'round', fill: _f, style: _s, class: _c, ...rest} = node.attrs;

  const style: React.CSSProperties = {
    fill: 'none', stroke,
    strokeWidth: Number(sw) || 3,
    strokeLinecap: slc as React.CSSProperties['strokeLinecap'],
    strokeLinejoin: slj as React.CSSProperties['strokeLinejoin'],
    strokeDasharray: 1,
    strokeDashoffset: 1 - progress,
  };

  if (node.kind === 'path') return <path pathLength={1} style={style} {...rest} />;
  if (node.kind === 'line') return <line pathLength={1} style={style} {...rest} />;
  if (node.kind === 'polyline') return <polyline pathLength={1} style={style} {...rest} />;
  return <polygon pathLength={1} style={style} {...rest} />;
};

type AnimatedFillProps = {node: FillNode; fillProgress: number; index: number; total: number};
const AnimatedFill: React.FC<AnimatedFillProps> = ({node, fillProgress, index, total}) => {
  const progress = elementProgress(fillProgress, index, total);
  const {stroke = '#1a1a1a', 'stroke-width': sw = '3', fill: _f, style: _s, class: _c, ...rest} = node.attrs;
  const style: React.CSSProperties = {
    fill: 'none', stroke, strokeWidth: Number(sw) || 3,
    strokeOpacity: progress, fillOpacity: 0,
  };
  if (node.kind === 'rect') return <rect style={style} {...rest} />;
  if (node.kind === 'circle') return <circle style={style} {...rest} />;
  return <ellipse style={style} {...rest} />;
};

type AnimatedTextProps = {node: TextNode; textProgress: number};
const AnimatedText: React.FC<AnimatedTextProps> = ({node, textProgress}) => {
  const {fill = '#1a1a1a', style: _s, class: _c, ...rest} = node.attrs;
  return (
    <text style={{fill, opacity: textProgress, fontFamily: 'sans-serif', fontSize: '16'}} {...rest}>
      {node.content}
    </text>
  );
};

export const SvgDrawer: React.FC<SvgDrawerProps> = ({svgContent, drawDurationFrames, sceneDurationFrames}) => {
  const frame = useCurrentFrame();

  const allNodes = useMemo(() => parseSvgNodes(svgContent || ''), [svgContent]);
  const viewBox = useMemo(() => extractViewBox(svgContent || ''), [svgContent]);

  const pathNodes = useMemo(() => allNodes.filter((n): n is PathNode =>
    n.kind === 'path' || n.kind === 'line' || n.kind === 'polyline' || n.kind === 'polygon'), [allNodes]);
  const fillNodes = useMemo(() => allNodes.filter((n): n is FillNode =>
    n.kind === 'rect' || n.kind === 'circle' || n.kind === 'ellipse'), [allNodes]);
  const textNodes = useMemo(() => allNodes.filter((n): n is TextNode => n.kind === 'text'), [allNodes]);

  const drawProgress = interpolate(frame, [0, Math.max(1, drawDurationFrames)], [0, 1], {extrapolateRight: 'clamp'});
  const fillProgress = interpolate(frame,
    [Math.max(0, drawDurationFrames * 0.4), Math.max(1, drawDurationFrames * 1.1)],
    [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const textProgress = interpolate(frame,
    [Math.max(0, drawDurationFrames * 0.8), Math.max(1, drawDurationFrames * 1.3)],
    [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const sceneOpacity = interpolate(frame,
    [0, 8, Math.max(9, sceneDurationFrames - 12), sceneDurationFrames],
    [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: sceneOpacity,
      transform: `scale(${0.97 + drawProgress * 0.03})`}}>
      <div style={{background: 'linear-gradient(145deg, rgba(255,255,255,0.97), rgba(243,247,252,0.85))',
        border: '1.5px solid rgba(13,47,99,0.12)', borderRadius: 28, padding: '36px 44px',
        boxShadow: '0 24px 72px rgba(14,33,62,0.18)', display: 'flex',
        alignItems: 'center', justifyContent: 'center'}}>
        <svg viewBox={viewBox} xmlns="http://www.w3.org/2000/svg"
          style={{width: 'min(62vw, 1080px)', height: 'min(55vh, 620px)', overflow: 'visible'}}>
          {fillNodes.map((node, i) =>
            <AnimatedFill key={`fill-${i}`} node={node} fillProgress={fillProgress} index={i} total={fillNodes.length} />)}
          {pathNodes.map((node, i) =>
            <AnimatedPath key={`path-${i}`} node={node} drawProgress={drawProgress} index={i} total={pathNodes.length} />)}
          {textNodes.map((node, i) =>
            <AnimatedText key={`text-${i}`} node={node} textProgress={textProgress} />)}
        </svg>
      </div>
    </AbsoluteFill>
  );
};