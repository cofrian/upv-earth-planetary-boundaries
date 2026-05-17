import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/google-fonts/InterTight';
import {colors, fonts, motion, type} from '../../brand/tokens';

loadFont('normal', {weights: ['400', '500'], subsets: ['latin']});

const WORDMARK = 'UPV-EARTH';
const TAG = 'Available now.';
const PROJECT_CODE = 'PROYII8 - UPV EARTH';

export const Act6CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const SCENE = 420; // 14s

  const sLogo = spring({frame, fps, config: motion.reveal});
  const logoScale = interpolate(sLogo, [0, 1], [0.94, 1]);
  const logoOpacity = interpolate(sLogo, [0, 1], [0, 1]);

  const sTag = spring({frame: Math.max(0, frame - 18), fps, config: motion.reveal});
  const tagY = interpolate(sTag, [0, 1], [14, 0]);
  const tagOpacity = interpolate(sTag, [0, 1], [0, 0.78]);

  const sLogos = spring({frame: Math.max(0, frame - 40), fps, config: motion.reveal});
  const logosY = interpolate(sLogos, [0, 1], [14, 0]);
  const logosOpacity = interpolate(sLogos, [0, 1], [0, 1]);

  // Glow pulse
  const glowPulse = 1 + Math.sin((frame / fps) * Math.PI * 1.1) * 0.05;

  const fadeIn = interpolate(frame, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [SCENE - 30, SCENE], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const visible = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        fontFamily: fonts.display,
        justifyContent: 'center',
        alignItems: 'center',
        opacity: visible,
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: 1400,
          height: 520,
          background: `radial-gradient(ellipse at center, ${colors.accent} 0%, rgba(16,163,127,0) 60%)`,
          filter: 'blur(110px)',
          opacity: 0.20,
          transform: `scale(${glowPulse})`,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 28,
          position: 'relative',
        }}
      >
        <div
          style={{
            color: colors.textMain,
            fontSize: type.wordmark.size,
            fontWeight: type.wordmark.weight,
            letterSpacing: type.wordmark.tracking,
            lineHeight: 1,
            transform: `scale(${logoScale})`,
            opacity: logoOpacity,
          }}
        >
          {WORDMARK}
        </div>
        <div
          style={{
            color: colors.textMuted,
            fontSize: type.cta.size,
            fontWeight: 400,
            letterSpacing: '-0.01em',
            opacity: tagOpacity,
            transform: `translateY(${tagY}px)`,
          }}
        >
          {TAG}
        </div>
        <div
          style={{
            marginTop: 12,
            paddingTop: 24,
            borderTop: `1px solid ${colors.line}`,
            color: colors.accent,
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: '0.08em',
            opacity: tagOpacity,
            transform: `translateY(${tagY}px)`,
          }}
        >
          {PROJECT_CODE}
        </div>
      </div>

      {/* Institutional logos at the bottom — inverted on light bg so they read */}
      <div
        style={{
          position: 'absolute',
          bottom: 90,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 60,
          opacity: logosOpacity,
          transform: `translateY(${logosY}px)`,
          filter: 'brightness(0)',
        }}
      >
        <Img src={staticFile('brand/etsinf-logo.svg')} style={{height: 64, width: 'auto'}} />
        <div style={{width: 1, height: 48, background: colors.line, filter: 'none'}} />
        <Img src={staticFile('brand/upv-logo.svg')} style={{height: 56, width: 'auto'}} />
      </div>
    </AbsoluteFill>
  );
};
