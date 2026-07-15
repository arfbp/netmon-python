import type { Config } from "tailwindcss";

// Design tokens for the NOC-style dashboard (Step 7). Grounded in the
// actual subject — a tool that pings the internet and reports health —
// rather than a generic dark-mode default. See the severity spectrum
// below: it's a deliberate hue progression (teal -> emerald -> amber ->
// orange -> red -> slate), not a random six-color assignment.
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0A0D14", // deep blue-black, not pure black — a "radar screen" undertone
          surface: "#12151F",
          "surface-hover": "#191D2A",
        },
        border: {
          DEFAULT: "#232838",
        },
        content: {
          DEFAULT: "#E7EAF2",
          muted: "#7C8494",
        },
        accent: {
          DEFAULT: "#22D3EE", // cyan — the "sweep/scan" color, used for brand + focus rings only
        },
        severity: {
          excellent: "#2DD4BF",
          good: "#34D399",
          warning: "#FBBF24",
          high: "#FB923C",
          critical: "#EF4444",
          offline: "#64748B", // slate, not literal black — invisible otherwise on this background
        },
      },
      fontFamily: {
        // System stacks only — deliberate for a self-hosted, local-first
        // tool: no external font CDN calls at runtime.
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Inter",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SF Mono",
          "Cascadia Code",
          "JetBrains Mono",
          "Consolas",
          "monospace",
        ],
      },
      animation: {
        sweep: "sweep 3s ease-in-out infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
      },
      keyframes: {
        sweep: {
          "0%, 100%": { transform: "translateX(-100%)" },
          "50%": { transform: "translateX(100%)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
