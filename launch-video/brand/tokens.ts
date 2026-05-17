// Paleta clara estilo ChatGPT / OpenAI marketing.
// Mantenemos el acento emerald de la marca UPV-EARTH.

export const colors = {
  bg: '#FFFFFF',
  bgSoft: '#F7F7F8',
  bgWarm: '#FAFAF8',
  textMain: '#0D0D0D',
  textMuted: '#565869',
  textSubtle: '#8E8EA0',
  accent: '#10A37F', // ChatGPT-style teal/green
  accentBright: '#10B981',
  accentSoft: 'rgba(16, 163, 127, 0.10)',
  line: '#E5E5E5',
  lineSoft: '#EFEFEF',
  white: '#FFFFFF',
  black: '#0D0D0D',
} as const;

export const fonts = {
  display: '"Inter Tight", "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
} as const;

export const motion = {
  manifesto: {damping: 22, mass: 0.6},
  cursor: {damping: 18, stiffness: 90},
  reveal: {damping: 20, mass: 0.7},
} as const;

export const type = {
  hook: {size: 124, weight: 500, tracking: '-0.04em'},
  headline: {size: 96, weight: 500, tracking: '-0.03em'},
  subtitle: {size: 48, weight: 400, tracking: '-0.02em'},
  chyronTitle: {size: 28, weight: 600, tracking: '-0.01em'},
  chyronBody: {size: 18, weight: 400, tracking: '0'},
  wordmark: {size: 148, weight: 500, tracking: '-0.05em'},
  tagline: {size: 32, weight: 400, tracking: '-0.02em'},
  cta: {size: 28, weight: 400, tracking: '-0.01em'},
} as const;
