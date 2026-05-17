import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont} from '@remotion/google-fonts/InterTight';
import {colors, fonts, motion, type} from '../../brand/tokens';

loadFont('normal', {weights: ['400', '500'], subsets: ['latin']});

const HEADLINE = 'Fifty thousand papers.';
const SUBTITLE = 'One university. Nowhere to search them as one mind.';

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

export const Act2Manifesto: React.FC = () => {
  const frame = useCurrentFrame();
  const DURATION = 360;
  const fadeIn = interpolate(frame, [0, 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [DURATION - 24, DURATION], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
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
      }}
    >
      {/* Subtle radial highlight */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 55%, ${colors.accentSoft} 0%, rgba(255,255,255,0) 60%)`,
          pointerEvents: 'none',
        }}
      />
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 48, position: 'relative'}}>
        <SpringLine
          text={HEADLINE}
          startFrame={10}
          size={type.headline.size}
          weight={type.headline.weight}
          tracking={type.headline.tracking}
          color={colors.textMain}
        />
        <SpringLine
          text={SUBTITLE}
          startFrame={110}
          size={type.subtitle.size}
          weight={type.subtitle.weight}
          tracking={type.subtitle.tracking}
          color={colors.textMuted}
        />
      </div>
    </AbsoluteFill>
  );
};
