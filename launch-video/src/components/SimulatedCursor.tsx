import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {motion} from '../../brand/tokens';

// Cursor that replays a .cursor.json recorded by Playwright.
// Coordinates are in page space (1920x1080 viewport) = stage space at full-bleed.

type CursorEvent = {tMs: number; action: string; x: number; y: number};

type Props = {
  events: CursorEvent[];
  clipDurationSec: number;
  /** Frames to offset the cursor timeline (in scene frames). Use to align with videoStartFrame. */
  startOffsetFrames?: number;
};

const CursorSVG: React.FC<{x: number; y: number; opacity?: number; scale?: number}> = ({
  x,
  y,
  opacity = 1,
  scale = 1,
}) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(-4px, -4px) scale(${scale})`,
      transformOrigin: '4px 4px',
      opacity,
      filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.35))',
      pointerEvents: 'none',
    }}
  >
    <svg width={32} height={36} viewBox="0 0 28 32" style={{display: 'block', overflow: 'visible'}}>
      <path
        d="M3 2 L25 16 L15 17.5 L21 28 L17 30 L11 19 L3 25 Z"
        fill="#FFFFFF"
        stroke="#0D0D0D"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
    </svg>
  </div>
);

export const SimulatedCursor: React.FC<Props> = ({events, clipDurationSec, startOffsetFrames = 0}) => {
  const frame = useCurrentFrame() - startOffsetFrames;
  const {fps} = useVideoConfig();

  if (events.length === 0) return null;

  const tMs = (frame / fps) * 1000;

  let prev = events[0];
  let next = events[events.length - 1];
  for (let i = 0; i < events.length - 1; i++) {
    if (tMs >= events[i].tMs && tMs <= events[i + 1].tMs) {
      prev = events[i];
      next = events[i + 1];
      break;
    }
    if (tMs > events[events.length - 1].tMs) {
      prev = events[events.length - 1];
      next = events[events.length - 1];
    }
  }

  const segDur = Math.max(1, next.tMs - prev.tMs);
  const segLocalMs = Math.max(0, Math.min(segDur, tMs - prev.tMs));
  const segFrame = (segLocalMs / 1000) * fps;
  const segTotalFrames = Math.max(1, (segDur / 1000) * fps);
  const t = spring({frame: segFrame, fps, config: motion.cursor, durationInFrames: segTotalFrames});
  const x = interpolate(t, [0, 1], [prev.x, next.x]);
  const y = interpolate(t, [0, 1], [prev.y, next.y]);

  // Ripples on click_down
  const RIPPLE_LIFE = 14;
  const ripples = events
    .filter((e) => e.action === 'click_down')
    .map((e, i) => {
      const evFrame = (e.tMs / 1000) * fps;
      const age = frame - evFrame;
      if (age < 0 || age > RIPPLE_LIFE) return null;
      const r = interpolate(age, [0, RIPPLE_LIFE], [22, 70]);
      const o = interpolate(age, [0, RIPPLE_LIFE], [0.55, 0]);
      return (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: e.x - r,
            top: e.y - r,
            width: r * 2,
            height: r * 2,
            borderRadius: '50%',
            border: '2px solid #FFFFFF',
            opacity: o,
            pointerEvents: 'none',
            mixBlendMode: 'difference',
          }}
        />
      );
    });

  // Click pulse
  let scale = 1;
  for (const e of events) {
    if (e.action === 'click_down') {
      const evFrame = (e.tMs / 1000) * fps;
      const age = frame - evFrame;
      if (age >= 0 && age <= 6) {
        scale = interpolate(age, [0, 3, 6], [1, 0.82, 1]);
        break;
      }
    }
  }

  // Fade cursor in/out at boundaries
  const fadeIn = interpolate(frame, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const totalFrames = clipDurationSec * fps;
  const fadeOut = interpolate(frame, [totalFrames - 10, totalFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cursorOpacity = Math.min(fadeIn, fadeOut);

  // Trail
  const trailFrames = [2, 4, 6];
  const trailOpacities = [0.28, 0.14, 0.06];
  const trail = trailFrames.map((delta, i) => {
    const tPast = tMs - (delta / fps) * 1000;
    let pPrev = events[0];
    let pNext = events[events.length - 1];
    for (let k = 0; k < events.length - 1; k++) {
      if (tPast >= events[k].tMs && tPast <= events[k + 1].tMs) {
        pPrev = events[k];
        pNext = events[k + 1];
        break;
      }
    }
    const sd = Math.max(1, pNext.tMs - pPrev.tMs);
    const sl = Math.max(0, Math.min(sd, tPast - pPrev.tMs));
    const px = pPrev.x + (pNext.x - pPrev.x) * (sl / sd);
    const py = pPrev.y + (pNext.y - pPrev.y) * (sl / sd);
    return <CursorSVG key={`t-${i}`} x={px} y={py} opacity={trailOpacities[i] * cursorOpacity} />;
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {trail}
      <CursorSVG x={x} y={y} opacity={cursorOpacity} scale={scale} />
      {ripples}
    </AbsoluteFill>
  );
};
