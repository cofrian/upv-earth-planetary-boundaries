import React from 'react';
import {AbsoluteFill} from 'remotion';
import {fonts, colors} from '../../brand/tokens';

export const ProjectWatermark: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        position: 'fixed',
        top: 20,
        right: 24,
        pointerEvents: 'none',
        zIndex: 1000,
      }}
    >
      <div
        style={{
          fontFamily: fonts.display,
          fontSize: 12,
          fontWeight: 500,
          letterSpacing: '0.05em',
          color: colors.textMuted,
          opacity: 0.5,
          textAlign: 'right',
          lineHeight: 1.4,
        }}
      >
        <div>PROYII8</div>
        <div>UPV EARTH</div>
      </div>
    </AbsoluteFill>
  );
};
