import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/google-fonts/InterTight';
import {colors, fonts, motion, type} from '../../brand/tokens';

loadFont('normal', {weights: ['400', '500'], subsets: ['latin']});

const WORDMARK = 'UPV-EARTH';
const TAGLINE = 'A research engine for a habitable Earth.';

export const Act3Reveal: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const DURATION = 180;

  const logoSpring = spring({frame, fps, config: motion.reveal});
  const logoScale = interpolate(logoSpring, [0, 1], [0.92, 1]);
  const logoOpacity = interpolate(logoSpring, [0, 1], [0, 1]);

  const taglineSpring = spring({frame: Math.max(0, frame - 32), fps, config: motion.reveal});
  const taglineY = interpolate(taglineSpring, [0, 1], [16, 0]);
  const taglineOpacity = interpolate(taglineSpring, [0, 1], [0, 0.78]);

  // Glow grows + soft pulse
  const glowGrow = interpolate(frame, [0, 30], [0.85, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const glowPulse = 1 + Math.sin((frame / fps) * Math.PI * 0.8) * 0.04;
  const glowScale = glowGrow * glowPulse;

  const fadeIn = interpolate(frame, [0, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [DURATION - 16, DURATION], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
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
          width: 1300,
          height: 480,
          background: `radial-gradient(ellipse at center, ${colors.accent} 0%, rgba(16,163,127,0) 60%)`,
          filter: 'blur(110px)',
          opacity: 0.18,
          transform: `scale(${glowScale})`,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 36,
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
            fontSize: type.tagline.size,
            fontWeight: 400,
            letterSpacing: type.tagline.tracking,
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
          }}
        >
          {TAGLINE}
        </div>
      </div>
    </AbsoluteFill>
  );
};
