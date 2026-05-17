import React from 'react';
import {AbsoluteFill} from 'remotion';
import {colors, fonts} from '../../brand/tokens';

// Full-bleed product window. The recording fills the stage; we add a thin
// translucent browser bar at the very top with traffic-light dots + URL.

export const BROWSER = {
  stageW: 1920,
  stageH: 1080,
  topBarH: 44,
  // The video area is the entire stage; the top bar floats over the top edge.
  videoX: 0,
  videoY: 0,
  videoW: 1920,
  videoH: 1080,
};

// Page coords are already 1920x1080 (Playwright viewport).
// At full-bleed, the on-stage coord equals the in-page coord exactly.
export const pageToStage = (xInPage: number, yInPage: number) => ({
  x: xInPage,
  y: yInPage,
});

type Props = {
  children: React.ReactNode;
  url: string;
};

export const BrowserFrame: React.FC<Props> = ({children, url}) => {
  return (
    <AbsoluteFill>
      {/* Full-bleed product surface */}
      <AbsoluteFill>{children}</AbsoluteFill>

      {/* Translucent top bar */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          right: 0,
          height: BROWSER.topBarH,
          background: 'rgba(255, 255, 255, 0.78)',
          backdropFilter: 'blur(14px)',
          borderBottom: `1px solid ${colors.line}`,
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 18,
          paddingRight: 18,
          fontFamily: fonts.mono,
          fontSize: 13,
          color: colors.textMuted,
          gap: 12,
        }}
      >
        {/* Traffic light dots */}
        <div style={{display: 'flex', gap: 8}}>
          <span style={{width: 12, height: 12, borderRadius: 6, background: '#ff5f57'}} />
          <span style={{width: 12, height: 12, borderRadius: 6, background: '#febc2e'}} />
          <span style={{width: 12, height: 12, borderRadius: 6, background: '#28c840'}} />
        </div>
        {/* URL pill */}
        <div
          style={{
            flex: '0 1 auto',
            marginLeft: 14,
            padding: '6px 16px',
            borderRadius: 999,
            background: colors.bgSoft,
            border: `1px solid ${colors.lineSoft}`,
            color: colors.textMain,
            letterSpacing: 0.2,
          }}
        >
          {url}
        </div>
      </div>
    </AbsoluteFill>
  );
};
