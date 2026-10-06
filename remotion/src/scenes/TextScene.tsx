import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

import {Branding, TimelineItem} from '../types';

const FONT = "Inter, 'Segoe UI', sans-serif";

type Props = {
  item: TimelineItem;
  branding: Branding;
  asVisual?: boolean;
};

export const TextScene: React.FC<Props> = ({item, branding, asVisual}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], {extrapolateRight: 'clamp'});
  const style = item.style ?? 'caption';

  if (asVisual || style === 'hook' || style === 'title') {
    return (
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          padding: '8%',
          opacity,
        }}
      >
        <div
          style={{
            color: branding.text,
            fontFamily: FONT,
            fontSize: style === 'caption' ? 64 : 92,
            fontWeight: 800,
            textAlign: 'center',
            lineHeight: 1.15,
            textShadow: '0 4px 24px rgba(0,0,0,0.55)',
          }}
        >
          {item.text}
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        padding: '0 6% 14%',
        opacity,
      }}
    >
      <div
        style={{
          color: branding.text,
          backgroundColor: 'rgba(10, 14, 23, 0.78)',
          border: `2px solid ${branding.primary}`,
          borderRadius: 24,
          padding: '22px 32px',
          fontFamily: FONT,
          fontSize: 48,
          fontWeight: 600,
          textAlign: 'center',
          lineHeight: 1.3,
        }}
      >
        {item.text}
      </div>
    </AbsoluteFill>
  );
};
