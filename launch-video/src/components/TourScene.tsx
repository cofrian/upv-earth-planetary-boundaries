import React from 'react';
import {AbsoluteFill, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {colors, fonts, type} from '../../brand/tokens';
import {BrowserFrame} from './BrowserFrame';
import {SimulatedCursor} from './SimulatedCursor';

export type TourSceneProps = {
  url: string;
  title: string;
  description: string;
  videoSrc: string;
  events: {tMs: number; action: string; x: number; y: number}[];
  durationInFrames: number;
  overlay?: React.ReactNode;
  videoStartFrame?: number;
  videoEndFrame?: number;
  /** Number of seconds at start to keep title visible. After that it fades out. */
  chyronVisibleSec?: number;
};

const DEFAULT_CHYRON_SEC = 6.5;

export const TourScene: React.FC<TourSceneProps> = ({
  url,
  title,
  description,
  videoSrc,
  events,
  durationInFrames,
  overlay,
  videoStartFrame,
  videoEndFrame,
  chyronVisibleSec = DEFAULT_CHYRON_SEC,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Clip-level fade in/out
  const fadeIn = interpolate(frame, [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fadeOut = interpolate(frame, [durationInFrames - 12, durationInFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const visible = Math.min(fadeIn, fadeOut);

  const clipDurSec = durationInFrames / fps;

  // Chyron: appears with spring at start, holds, then fades out
  const chyronIn = spring({frame: Math.max(0, frame - 14), fps, config: {damping: 22, mass: 0.6}});
  const chyronOutStart = chyronVisibleSec * fps;
  const chyronOut = interpolate(frame, [chyronOutStart, chyronOutStart + 30], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const chyronOpacity = Math.min(chyronIn, chyronOut);
  const chyronY = interpolate(chyronIn, [0, 1], [10, 0]);

  return (
    <AbsoluteFill style={{backgroundColor: colors.bgSoft, opacity: visible}}>
      <BrowserFrame url={url}>
        <OffthreadVideo
          src={staticFile(videoSrc)}
          style={{width: 1920, height: 1080, objectFit: 'cover', display: 'block'}}
          startFrom={videoStartFrame}
          endAt={videoEndFrame}
          muted
        />
      </BrowserFrame>

      {/* Cursor overlay (page coords = stage coords) */}
      <SimulatedCursor events={events} clipDurationSec={clipDurSec} />

      {/* Title chyron bottom-left, auto-hide */}
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
          maxWidth: 700,
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

      {overlay}
    </AbsoluteFill>
  );
};
