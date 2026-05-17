import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, fonts, type} from '../../brand/tokens';
import {BrowserFrame} from '../components/BrowserFrame';

// Upload tour scene with a JUMP-CUT that hides the pipeline wait time.
//
// Segment 1 (drop + click "Procesar PDF"): plays source frames 30-180 (1-6s)
// Segment 2 (pipeline complete + results): plays source from frame 390 (13s)
// Between them: a quick white flash + crossfade so the user perceives "instant".

type Props = {
  url: string;
  title: string;
  description: string;
  durationInFrames: number;
};

const SEG1_END = 135; // 4.5s scene frame: end of segment 1
const CROSSFADE = 22; // frames of overlap between seg1 fade-out and seg2 fade-in
const JUMP_FROM_FRAME = 390; // source frame to start segment 2 (≈13s into source)

export const UploadScene: React.FC<Props> = ({url, title, description, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Scene level fade in/out
  const fadeIn = interpolate(frame, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 12, durationInFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const visible = Math.min(fadeIn, fadeOut);

  // Crossfade between the two segments
  const seg1Op = interpolate(frame, [SEG1_END - CROSSFADE, SEG1_END], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const seg2Op = interpolate(frame, [SEG1_END - CROSSFADE, SEG1_END], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // White flash at the cut to imply "instant processing"
  const flash = interpolate(frame, [SEG1_END - CROSSFADE, SEG1_END - CROSSFADE / 2, SEG1_END], [0, 0.45, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Chyron timing
  const chyronIn = spring({frame: Math.max(0, frame - 14), fps, config: {damping: 22, mass: 0.6}});
  const chyronOutStart = 6.5 * fps;
  const chyronOut = interpolate(frame, [chyronOutStart, chyronOutStart + 30], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const chyronOpacity = Math.min(chyronIn, chyronOut);
  const chyronY = interpolate(chyronIn, [0, 1], [10, 0]);

  // "Processing… complete" pill that appears briefly at the cut
  const pillIn = interpolate(frame, [SEG1_END - CROSSFADE, SEG1_END], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pillOut = interpolate(frame, [SEG1_END + 30, SEG1_END + 60], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pillOpacity = Math.min(pillIn, pillOut);

  return (
    <AbsoluteFill style={{backgroundColor: colors.bgSoft, opacity: visible}}>
      <BrowserFrame url={url}>
        {/* Segment 1: drop + click */}
        <AbsoluteFill style={{opacity: seg1Op}}>
          <OffthreadVideo
            src={staticFile('recordings/05-upload-pdf.webm')}
            style={{width: 1920, height: 1080, objectFit: 'cover', display: 'block'}}
            startFrom={30}
            endAt={SEG1_END + 30}
            muted
          />
        </AbsoluteFill>
        {/* Segment 2: results — wrapped in Sequence so source playback starts when segment becomes visible */}
        <Sequence from={SEG1_END - CROSSFADE} durationInFrames={durationInFrames - (SEG1_END - CROSSFADE)}>
          <AbsoluteFill style={{opacity: seg2Op}}>
            <OffthreadVideo
              src={staticFile('recordings/05-upload-pdf.webm')}
              style={{width: 1920, height: 1080, objectFit: 'cover', display: 'block'}}
              startFrom={JUMP_FROM_FRAME}
              muted
            />
          </AbsoluteFill>
        </Sequence>
      </BrowserFrame>

      {/* White flash at the cut */}
      <AbsoluteFill style={{backgroundColor: '#FFFFFF', opacity: flash, pointerEvents: 'none'}} />

      {/* "Pipeline complete" pill at top-right around the cut */}
      <div
        style={{
          position: 'absolute',
          top: 70,
          right: 56,
          padding: '10px 18px',
          background: 'rgba(255,255,255,0.96)',
          border: `1px solid ${colors.line}`,
          borderRadius: 999,
          fontFamily: fonts.display,
          fontSize: 16,
          fontWeight: 600,
          color: colors.textMain,
          letterSpacing: '-0.01em',
          opacity: pillOpacity,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
        }}
      >
        <span style={{width: 10, height: 10, borderRadius: 5, background: colors.accent}} />
        Pipeline complete · 10 stages
      </div>

      {/* Title chyron bottom-left */}
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
          opacity: chyronOpacity,
          transform: `translateY(${chyronY}px)`,
          maxWidth: 720,
        }}
      >
        <div
          style={{
            color: colors.textMain,
            fontSize: type.chyronTitle.size,
            fontWeight: type.chyronTitle.weight,
            letterSpacing: type.chyronTitle.tracking,
            lineHeight: 1.15,
          }}
        >
          {title}
        </div>
        <div
          style={{
            color: colors.textMuted,
            fontSize: type.chyronBody.size,
            fontWeight: type.chyronBody.weight,
            marginTop: 6,
            lineHeight: 1.45,
          }}
        >
          {description}
        </div>
      </div>
    </AbsoluteFill>
  );
};
