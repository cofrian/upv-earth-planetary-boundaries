import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#040806",
        surface: {
          DEFAULT: "#0a1410",
          1: "#0a1410",
          2: "#0f1d18",
          3: "#13261f",
        },
        line: {
          DEFAULT: "#1c2c25",
          strong: "#2a4034",
          accent: "#1e6b4f",
        },
        textMain: "#e6f4ed",
        textSubtle: "#a9c5b7",
        textMuted: "#6f8a7c",
        emerald: {
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          glow: "#34d39940",
        },
        accent: "#34d399",
        accentSoft: "#10b981",
        accentDeep: "#047857",
        amber: "#fbbf24",
        rose: "#f87171",
        // legacy aliases
        panel: "#0a1410",
        panelSoft: "#0f1d18",
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
        glow: "0 0 0 1px rgba(52,211,153,0.18), 0 22px 48px rgba(4,12,9,0.55)",
        emerald: "0 0 0 1px rgba(52,211,153,0.45), 0 10px 28px rgba(16,185,129,0.18)",
        soft: "0 1px 0 rgba(255,255,255,0.04) inset, 0 18px 36px rgba(4,12,9,0.55)",
      },
      backgroundImage: {
        "grid-fade":
          "linear-gradient(180deg, rgba(13,30,24,0.85) 0%, rgba(4,8,6,1) 100%)",
        "emerald-radial":
          "radial-gradient(circle at 30% 0%, rgba(16,185,129,0.18), transparent 55%)",
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
