import React from 'react';
import {AbsoluteFill} from 'remotion';

import {Branding} from '../types';

export const BrandLayer: React.FC<{branding: Branding}> = ({branding}) => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    <div
      style={{
        position: 'absolute',
        top: '3.5%',
        left: '5%',
        width: 140,
        height: 12,
        borderRadius: 8,
        background: `linear-gradient(90deg, ${branding.primary}, ${branding.secondary})`,
      }}
    />
    <div
      style={{
        position: 'absolute',
        top: '3.2%',
        right: '5%',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        backgroundColor: 'rgba(10, 14, 23, 0.65)',
        borderRadius: 999,
        padding: '12px 26px',
      }}
    >
      <div
        style={{
          width: 20,
          height: 20,
          borderRadius: 999,
          backgroundColor: branding.accent,
        }}
      />
      <span
        style={{
          color: branding.text,
          fontFamily: "Inter, 'Segoe UI', sans-serif",
          fontSize: 40,
          fontWeight: 700,
          letterSpacing: 1,
        }}
      >
        {branding.handle}
      </span>
    </div>
  </AbsoluteFill>
);
