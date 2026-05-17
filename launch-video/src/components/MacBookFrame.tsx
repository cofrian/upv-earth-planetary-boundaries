import React from 'react';

// Drawn MacBook Pro 16" frame (no stock images).
// Returns the wrapper + screen viewport. Children render INSIDE the screen.
// Geometry constants are exported so cursor can project page coords onto stage.

export const MAC = {
  // Position of the chassis on the 1920x1080 stage
  chassisX: 620,
  chassisY: 140,
  chassisW: 1220,
  chassisH: 800,
  // Screen area inside the chassis (relative to chassis top-left)
  screenInsetX: 40,
  screenInsetY: 30,
  screenW: 1140,
  screenH: 641, // 16:9 inside
};

export const macToStage = (xInPage: number, yInPage: number, pageW = 1920, pageH = 1080) => ({
  x: MAC.chassisX + MAC.screenInsetX + (xInPage / pageW) * MAC.screenW,
  y: MAC.chassisY + MAC.screenInsetY + (yInPage / pageH) * MAC.screenH,
});

export const MacBookFrame: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: MAC.chassisX,
        top: MAC.chassisY,
        width: MAC.chassisW,
        height: MAC.chassisH,
        filter: 'drop-shadow(0 60px 60px rgba(0,0,0,0.55))',
        ...style,
      }}
    >
      {/* Lid (display bezel) */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: MAC.chassisW,
          height: MAC.screenInsetY + MAC.screenH + 30,
          background: 'linear-gradient(180deg, #1d1f22 0%, #131517 100%)',
          borderRadius: 22,
          boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.04)',
        }}
      >
        {/* Camera notch */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 8,
            transform: 'translateX(-50%)',
            width: 180,
            height: 18,
            background: '#0a0a0c',
            borderRadius: 9,
          }}
        />
        {/* Screen */}
        <div
          style={{
            position: 'absolute',
            left: MAC.screenInsetX,
            top: MAC.screenInsetY,
            width: MAC.screenW,
            height: MAC.screenH,
            backgroundColor: '#000',
            borderRadius: 6,
            overflow: 'hidden',
          }}
        >
          {children}
        </div>
      </div>

      {/* Hinge gap */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: MAC.screenInsetY + MAC.screenH + 30,
          width: MAC.chassisW,
          height: 8,
          background: 'linear-gradient(180deg, #0a0b0c 0%, #2a2c2f 100%)',
        }}
      />

      {/* Base (deck) */}
      <div
        style={{
          position: 'absolute',
          left: -28,
          top: MAC.screenInsetY + MAC.screenH + 38,
          width: MAC.chassisW + 56,
          height: 22,
          background: 'linear-gradient(180deg, #2a2c2f 0%, #1a1c1e 100%)',
          borderBottomLeftRadius: 18,
          borderBottomRightRadius: 18,
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05)',
        }}
      >
        {/* Trackpad notch */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 0,
            transform: 'translateX(-50%)',
            width: 160,
            height: 6,
            background: '#0e0f10',
            borderRadius: 3,
          }}
        />
      </div>
    </div>
  );
};
