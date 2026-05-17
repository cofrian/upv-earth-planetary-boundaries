import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {loadFont} from '@remotion/google-fonts/InterTight';
import {colors, fonts, type} from '../../brand/tokens';

loadFont('normal', {weights: ['400', '500'], subsets: ['latin']});

const TEXT = 'Climate science has a trust problem.';

export const Act1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  // Letter reveal with stagger, then longer dwell (extended from 180 to 240 frames)
  const charStagger = 1.3;
  const fadeOut = interpolate(frame, [210, 240], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.bg,
        fontFamily: fonts.display,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 120,
        opacity: fadeOut,
      }}
    >
      <div
        style={{
          color: colors.textMain,
          fontSize: type.hook.size,
          fontWeight: type.hook.weight,
          letterSpacing: type.hook.tracking,
          lineHeight: 1.05,
          textAlign: 'center',
          maxWidth: 1500,
        }}
      >
        {TEXT.split('').map((ch, i) => {
          const start = i * charStagger;
          const o = interpolate(frame, [start, start + 6], [0, 1], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          const yOff = interpolate(frame, [start, start + 10], [10, 0], {
            extrapolateLeft: 'clamp',
            extrapolateRight: 'clamp',
          });
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                opacity: o,
                transform: `translateY(${yOff}px)`,
                whiteSpace: 'pre',
              }}
            >
              {ch}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
