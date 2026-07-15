/**
 * Mirrors backend Pydantic schemas 1:1 — field names and optionality
 * must match (see STANDARDS.md). Source of truth:
 *   - Severity: backend/app/core/enums.py
 *   - PingLatestResponse: backend/app/api/v1/schemas.py
 *   - PingResultEvent payload shape: backend/app/events/schemas.py
 */

export type Severity = "excellent" | "good" | "warning" | "high" | "critical" | "offline";

export interface PingLatest {
  target: string;
  timestamp: string; // ISO 8601
  latency_ms: number | null;
  is_timeout: boolean;
  jitter_ms: number | null;
  rolling_avg_ms: number | null;
  packet_loss_pct: number;
  severity: Severity;
}

/** The payload shape of a `ping_result` WebSocket message — same fields
 * as PingLatest plus `occurred_at` (event time) instead of `timestamp`,
 * matching `PingResultEvent`'s dataclass fields exactly. */
export interface PingResultPayload {
  occurred_at: string;
  target: string;
  latency_ms: number | null;
  is_timeout: boolean;
  jitter_ms: number | null;
  rolling_avg_ms: number | null;
  packet_loss_pct: number;
  severity: Severity;
}

/** Severity worst-to-best ranking, mirroring Severity.rank() in
 * backend/app/core/enums.py — kept in sync manually since it's a small,
 * stable enum; a generated-types pipeline would be overkill at this
 * project's size. */
export const SEVERITY_RANK: Record<Severity, number> = {
  excellent: 0,
  good: 1,
  warning: 2,
  high: 3,
  critical: 4,
  offline: 5,
};

export function worstSeverity(severities: Severity[]): Severity | null {
  if (severities.length === 0) return null;
  return severities.reduce((worst, current) =>
    SEVERITY_RANK[current] > SEVERITY_RANK[worst] ? current : worst,
  );
}
