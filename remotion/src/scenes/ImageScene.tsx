import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';

import {TimelineItem} from '../types';

export const ImageScene: React.FC<{item: TimelineItem}> = ({item}) => {
  const frame = useCurrentFrame();
  const scale =
    item.motion === 'slow_zoom'
      ? interpolate(frame, [0, Math.max(item.duration_frames, 1)], [1, 1.08], {
          extrapolateRight: 'clamp',
        })
      : 1;

  return (
    <AbsoluteFill style={{transform: `scale(${scale})`}}>
      <Img
        src={staticFile(item.asset_id ?? 'placeholder-1.png')}
        style={{
          width: '100%',
          height: '100%',
          objectFit: item.fit === 'contain' ? 'contain' : 'cover',
        }}
      />
    </AbsoluteFill>
  );
};
