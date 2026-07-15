/**
 * Raw hex values mirroring tailwind.config.ts's token system, for the
 * one context that can't consume Tailwind classes: ECharts' JS config
 * object. This is a deliberate, small duplication — keep these two
 * files in sync if the palette ever changes.
 */
export const CHART_COLORS = {
  bg: "#0A0D14",
  surface: "#12151F",
  border: "#232838",
  textMuted: "#7C8494",
  accent: "#22D3EE",
  series: ["#22D3EE", "#34D399", "#FBBF24", "#FB923C", "#F87171", "#A78BFA"],
} as const;
