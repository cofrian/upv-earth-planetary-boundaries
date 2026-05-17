import {AbsoluteFill} from 'remotion';

// TODO: SpringText
// Texto que aparece con spring animation (escala + opacidad + blur).
// Props previstos: children, startFrame, fontSize, weight, color, exitAt.
// Reutilizable en todos los actos para mantener consistencia tipográfica.

export const SpringText: React.FC<{children?: React.ReactNode}> = ({children}) => {
  return <AbsoluteFill>{children}</AbsoluteFill>;
};
