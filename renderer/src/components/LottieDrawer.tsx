import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Lottie, LottieAnimationData} from '@remotion/lottie';

type LottieDrawerProps = {
  lottieJson: string;
  drawDurationFrames: number;
  sceneDurationFrames: number;
};

export const LottieDrawer: React.FC<LottieDrawerProps> = ({
  lottieJson,
  drawDurationFrames,
  sceneDurationFrames,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const animationData = useMemo(() => {
    try {
      // Cast to the full Bodymovin structure expected by Remotion
      return JSON.parse(lottieJson) as LottieAnimationData;
    } catch (e) {
      console.error('Failed to parse Lottie JSON', e);
      return null;
    }
  }, [lottieJson]);

  if (!animationData) return null;

  // Cast to any for the arithmetic to bypass the 'unknown' field issues
  const {op, ip} = animationData as any;
  const lottieFrames = op - ip;
  const playbackSpeed = lottieFrames / drawDurationFrames;

  return (
    <AbsoluteFill style={{
      justifyContent: 'center',
      alignItems: 'center',
    }}>
      <div style={{width: '70%', height: '70%'}}>
        <Lottie
          animationData={animationData}
          playbackRate={playbackSpeed}
        />
      </div>
    </AbsoluteFill>
  );
};
