import type { Severity } from "@/types/ping";

/** Single source of truth mapping severity -> Tailwind classes.
 * Components reference this rather than hardcoding severity colors, so
 * a palette change is a one-line edit here (per STANDARDS.md's "no
 * inline hex colors in components" rule). */
export const SEVERITY_TEXT_CLASS: Record<Severity, string> = {
  excellent: "text-severity-excellent",
  good: "text-severity-good",
  warning: "text-severity-warning",
  high: "text-severity-high",
  critical: "text-severity-critical",
  offline: "text-severity-offline",
};

export const SEVERITY_BG_CLASS: Record<Severity, string> = {
  excellent: "bg-severity-excellent",
  good: "bg-severity-good",
  warning: "bg-severity-warning",
  high: "bg-severity-high",
  critical: "bg-severity-critical",
  offline: "bg-severity-offline",
};

export const SEVERITY_BORDER_CLASS: Record<Severity, string> = {
  excellent: "border-severity-excellent",
  good: "border-severity-good",
  warning: "border-severity-warning",
  high: "border-severity-high",
  critical: "border-severity-critical",
  offline: "border-severity-offline",
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  excellent: "Excellent",
  good: "Good",
  warning: "Warning",
  high: "High",
  critical: "Critical",
  offline: "Offline",
};
