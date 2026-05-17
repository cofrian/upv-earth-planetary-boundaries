import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/google-fonts/InterTight';
import {colors, fonts, motion, type} from '../../brand/tokens';

loadFont('normal', {weights: ['400', '500'], subsets: ['latin']});

const HEADLINE = 'The planet runs on evidence.';
const SUBTITLE = 'Now the evidence runs at the speed of a question.';

const SCREENS = [
  'recon/01-dashboard.png',
  'recon/02-analysis.png',
  'recon/03-papers.png',
  'recon/04-upload.png',
  'recon/05-paper-detail.png',
];

const SpringLine: React.FC<{
  text: string;
  startFrame: number;
  size: number;
  weight: number;
  tracking: string;
  color: string;
  opacityTarget?: number;
}> = ({text, startFrame, size, weight, tracking, color, opacityTarget = 1}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = Math.max(0, frame - startFrame);
  const s = spring({frame: local, fps, config: motion.manifesto});
  const y = interpolate(s, [0, 1], [22, 0]);
  const o = interpolate(s, [0, 1], [0, opacityTarget]);
  return (
    <div
      style={{
        color,
        fontSize: size,
        fontWeight: weight,
        letterSpacing: tracking,
        lineHeight: 1.1,
        transform: `translateY(${y}px)`,
        opacity: o,
        textAlign: 'center',
        maxWidth: 1500,
      }}
    >
      {text}
    </div>
  );
};

const BackdropScreen: React.FC<{src: string; index: number; total: number; sceneDur: number}> = ({src, index, total, sceneDur}) => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame, [0, sceneDur], [-30, 30]);
  const baseX = -200 + index * (2320 / (total - 1));
  const baseY = 80 + (index % 2 === 0 ? 0 : 220);
  return (
    <div
      style={{
        position: 'absolute',
        left: baseX + drift * (index % 2 === 0 ? 1 : -1),
        top: baseY,
        width: 760,
        height: 428,
        filter: 'blur(28px) saturate(0.6)',
        opacity: 0.10,
        borderRadius: 16,
        overflow: 'hidden',
      }}
    >
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </div>
  );
};

export const Act5Vision: React.FC = () => {
  const frame = useCurrentFrame();
  const SCENE = 360; // 12s

  const fadeIn = interpolate(frame, [0, 22], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [SCENE - 22, SCENE], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const visible = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        fontFamily: fonts.display,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 120,
        opacity: visible,
        overflow: 'hidden',
      }}
    >
      {SCREENS.map((s, i) => (
        <BackdropScreen key={s} src={s} index={i} total={SCREENS.length} sceneDur={SCENE} />
      ))}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 50%, ${colors.accentSoft} 0%, rgba(255,255,255,0) 60%)`,
          pointerEvents: 'none',
        }}
      />
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 48, position: 'relative'}}>
        <SpringLine
          text={HEADLINE}
          startFrame={14}
          size={type.headline.size}
          weight={type.headline.weight}
          tracking={type.headline.tracking}
          color={colors.textMain}
        />
        <SpringLine
          text={SUBTITLE}
          startFrame={108}
          size={type.subtitle.size}
          weight={type.subtitle.weight}
          tracking={type.subtitle.tracking}
          color={colors.textMuted}
        />
      </div>
    </AbsoluteFill>
  );
};
