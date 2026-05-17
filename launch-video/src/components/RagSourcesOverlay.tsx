import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, fonts, motion} from '../../brand/tokens';

const SOURCES = [
  {name: 'pb_reference_readable_en.pdf', meta: 'Planetary Boundaries — reference', chunks: 4},
  {name: 'corpus_pb_methodology.pdf', meta: 'UPV-EARTH · methodology', chunks: 3},
  {name: 'Larosa_2025_Environ_Res_Lett.pdf', meta: 'Env. Res. Lett. · freshwater use', chunks: 2},
  {name: 'aerosol_liquid_water_north_china.pdf', meta: 'Just uploaded · aerosol–water', chunks: 5},
];

const PdfIcon: React.FC = () => (
  <svg width={32} height={40} viewBox="0 0 32 40">
    <rect x={1} y={1} width={26} height={38} rx={3} fill="#ffffff" stroke={colors.accent} strokeWidth={1.5} />
    <path d="M20 1 L20 8 L27 8" fill="none" stroke={colors.accent} strokeWidth={1.5} />
    <text x={14} y={28} fontFamily={fonts.display} fontSize={9} fontWeight={600} fill={colors.accent} textAnchor="middle">
      PDF
    </text>
  </svg>
);

type Props = {
  startFrame: number;
  x?: number;
  y?: number;
  width?: number;
};

export const RagSourcesOverlay: React.FC<Props> = ({startFrame, x = 56, y = 96, width = 580}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Header containers fade in
  const headerOp = interpolate(frame, [startFrame, startFrame + 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        pointerEvents: 'none',
        fontFamily: fonts.display,
      }}
    >
      <div
        style={{
          color: colors.textMain,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          opacity: headerOp,
          marginBottom: 8,
          padding: '8px 14px',
          background: 'rgba(255, 255, 255, 0.94)',
          borderRadius: 999,
          border: `1px solid ${colors.line}`,
          display: 'inline-block',
          alignSelf: 'flex-start',
        }}
      >
        <span style={{color: colors.accent}}>● </span>
        Retrieval-Augmented Generation · 4 sources
      </div>
      {SOURCES.map((s, i) => {
        const localFrame = frame - (startFrame + 14 + i * 14);
        const sp = spring({frame: Math.max(0, localFrame), fps, config: motion.manifesto});
        const tx = interpolate(sp, [0, 1], [-30, 0]);
        const op = interpolate(sp, [0, 1], [0, 1]);
        return (
          <div
            key={s.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '12px 16px',
              background: 'rgba(255, 255, 255, 0.96)',
              border: `1px solid ${colors.line}`,
              borderRadius: 14,
              boxShadow: '0 6px 24px rgba(0,0,0,0.06)',
              transform: `translateX(${tx}px)`,
              opacity: op,
            }}
          >
            <PdfIcon />
            <div style={{display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0}}>
              <div
                style={{
                  color: colors.textMain,
                  fontSize: 17,
                  fontWeight: 500,
                  letterSpacing: '-0.01em',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: 480,
                }}
              >
                {s.name}
              </div>
              <div style={{color: colors.textMuted, fontSize: 13}}>
                {s.meta} · <span style={{color: colors.accent, fontWeight: 600}}>{s.chunks} chunks</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
