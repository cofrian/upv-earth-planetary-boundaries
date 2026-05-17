import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {colors, fonts} from '../../brand/tokens';

export const StackZoom: React.FC<{durationInFrames: number}> = ({durationInFrames}) => {
  const frame = useCurrentFrame();

  // Slow zoom from 0.98 → 1.06 across the scene
  const scale = interpolate(frame, [0, durationInFrames], [0.98, 1.06]);
  const translateX = interpolate(frame, [0, durationInFrames], [0, -10]);

  const fadeIn = interpolate(frame, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 14, durationInFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const visible = Math.min(fadeIn, fadeOut);

  // Chyron: visible for ~8s, then slow fade
  const titleSpring = interpolate(frame, [12, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const titleOut = interpolate(frame, [240, 280], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const titleVisible = Math.min(titleSpring, titleOut);

  return (
    <AbsoluteFill style={{backgroundColor: colors.bgSoft, opacity: visible, overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `scale(${scale}) translateX(${translateX}px)`,
          transformOrigin: 'center center',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Img
          src={staticFile('brand/stack.png')}
          style={{width: '94%', height: 'auto', maxHeight: '92%', display: 'block', objectFit: 'contain'}}
        />
      </div>

      {/* Floating caption chyron, bottom-left */}
      <div
        style={{
          position: 'absolute',
          left: 56,
          bottom: 56,
          padding: '18px 26px',
          background: 'rgba(255, 255, 255, 0.92)',
          backdropFilter: 'blur(14px)',
          borderRadius: 18,
          border: `1px solid ${colors.line}`,
          boxShadow: '0 12px 40px rgba(0,0,0,0.18)',
          fontFamily: fonts.display,
          opacity: titleVisible,
        }}
      >
        <div style={{color: colors.textMain, fontSize: 28, fontWeight: 600, letterSpacing: '-0.01em'}}>
          Engineered end to end.
        </div>
        <div style={{color: colors.textMuted, fontSize: 18, marginTop: 6}}>
          Next.js · FastAPI · SPECTER2 · Ollama · vLLM · SQLite.
        </div>
      </div>
    </AbsoluteFill>
  );
};
