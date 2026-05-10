import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#080406",
        surface: {
          DEFAULT: "#140a10",
          1: "#140a10",
          2: "#1d0f18",
          3: "#26131f",
        },
        line: {
          DEFAULT: "#262026",
          strong: "#3a2c34",
          accent: "#7e0334",
        },
        textMain: "#f1e6ee",
        textSubtle: "#c8b7c3",
        textMuted: "#8a7a82",
        // Magenta corporativa ETSINF como acento. Mantenemos el alias
        // `emerald.*` para que los componentes que aún usen `bg-emerald-500`
        // hereden automáticamente el nuevo tono sin cambios.
        emerald: {
          400: "#ec4079",
          500: "#d20a55",
          600: "#a80544",
          700: "#7e0334",
          glow: "#d20a5540",
        },
        magenta: {
          50: "#fff0f6",
          100: "#ffd6e6",
          200: "#ffadcc",
          300: "#ff7aa9",
          400: "#ec4079",
          500: "#d20a55",
          600: "#a80544",
          700: "#7e0334",
        },
        accent: "#d20a55",
        accentSoft: "#ec4079",
        accentDeep: "#7e0334",
        amber: "#fbbf24",
        rose: "#f87171",
        // legacy aliases
        panel: "#140a10",
        panelSoft: "#1d0f18",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(210,10,85,0.18), 0 22px 48px rgba(12,4,9,0.55)",
        emerald: "0 0 0 1px rgba(210,10,85,0.45), 0 10px 28px rgba(168,5,68,0.18)",
        soft: "0 1px 0 rgba(255,255,255,0.04) inset, 0 18px 36px rgba(12,4,9,0.55)",
      },
      backgroundImage: {
        "grid-fade":
          "linear-gradient(180deg, rgba(30,13,24,0.85) 0%, rgba(8,4,6,1) 100%)",
        "emerald-radial":
          "radial-gradient(circle at 30% 0%, rgba(210,10,85,0.18), transparent 55%)",
        "card-shine":
          "linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0))",
      },
      animation: {
        "fade-up": "fadeUp 0.45s ease-out both",
        shimmer: "shimmer 1.6s linear infinite",
        pulseSoft: "pulseSoft 2.4s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseSoft: {
          "0%,100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
