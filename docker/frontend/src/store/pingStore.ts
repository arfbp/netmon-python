import { create } from "zustand";

import type { ConnectionStatus } from "@/lib/websocket";
import type { PingLatest, PingResultPayload, Severity } from "@/types/ping";

const CHART_BUFFER_SIZE = 60; // ~2 minutes of history at a 2s ping interval

export interface TargetState {
  target: string;
  latencyMs: number | null;
  isTimeout: boolean;
  jitterMs: number | null;
  rollingAvgMs: number | null;
  packetLossPct: number;
  severity: Severity;
  updatedAt: string;
  /** Rolling buffer for the live chart — {t: epoch ms, v: latency|null}. */
  history: { t: number; v: number | null }[];
}

interface PingStoreState {
  connectionStatus: ConnectionStatus;
  targets: Record<string, TargetState>;
  setConnectionStatus: (status: ConnectionStatus) => void;
  hydrateFromLatest: (rows: PingLatest[]) => void;
  applyPingResult: (payload: PingResultPayload) => void;
}

function pushHistory(
  history: TargetState["history"],
  point: { t: number; v: number | null },
): TargetState["history"] {
  const next = [...history, point];
  return next.length > CHART_BUFFER_SIZE ? next.slice(next.length - CHART_BUFFER_SIZE) : next;
}

export const usePingStore = create<PingStoreState>((set) => ({
  connectionStatus: "connecting",
  targets: {},

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  hydrateFromLatest: (rows) =>
    set((state) => {
      const targets = { ...state.targets };
      for (const row of rows) {
        // Don't clobber a target that's already received live WS data
        // (which may be newer than this initial REST snapshot) with
        // stale initial-load data arriving late.
        if (targets[row.target]) continue;
        targets[row.target] = {
          target: row.target,
          latencyMs: row.latency_ms,
          isTimeout: row.is_timeout,
          jitterMs: row.jitter_ms,
          rollingAvgMs: row.rolling_avg_ms,
          packetLossPct: row.packet_loss_pct,
          severity: row.severity,
          updatedAt: row.timestamp,
          history: [{ t: new Date(row.timestamp).getTime(), v: row.latency_ms }],
        };
      }
      return { targets };
    }),

  applyPingResult: (payload) =>
    set((state) => {
      const existing = state.targets[payload.target];
      const point = { t: new Date(payload.occurred_at).getTime(), v: payload.latency_ms };
      return {
        targets: {
          ...state.targets,
          [payload.target]: {
            target: payload.target,
            latencyMs: payload.latency_ms,
            isTimeout: payload.is_timeout,
            jitterMs: payload.jitter_ms,
            rollingAvgMs: payload.rolling_avg_ms,
            packetLossPct: payload.packet_loss_pct,
            severity: payload.severity,
            updatedAt: payload.occurred_at,
            history: pushHistory(existing?.history ?? [], point),
          },
        },
      };
    }),
}));
