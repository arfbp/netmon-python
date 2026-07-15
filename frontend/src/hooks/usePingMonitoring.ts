import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { monitoringSocket } from "@/lib/websocket";
import { usePingStore } from "@/store/pingStore";
import type { PingResultPayload } from "@/types/ping";

/**
 * Wires real-time monitoring data into the app: fetches the initial
 * snapshot via REST (React Query — server state), then opens the
 * WebSocket connection and streams `ping_result` events into the
 * Zustand store (client-only real-time state) for the rest of the
 * app's lifetime.
 */
export function usePingMonitoring(): void {
  const hydrateFromLatest = usePingStore((state) => state.hydrateFromLatest);
  const applyPingResult = usePingStore((state) => state.applyPingResult);
  const setConnectionStatus = usePingStore((state) => state.setConnectionStatus);

  const { data } = useQuery({
    queryKey: ["ping", "latest"],
    queryFn: api.getLatestPingResults,
  });

  useEffect(() => {
    if (data) hydrateFromLatest(data);
  }, [data, hydrateFromLatest]);

  useEffect(() => {
    const unsubscribeStatus = monitoringSocket.onStatusChange(setConnectionStatus);
    const unsubscribeMessage = monitoringSocket.on("ping_result", (payload) => {
      applyPingResult(payload as PingResultPayload);
    });

    monitoringSocket.connect();

    return () => {
      unsubscribeStatus();
      unsubscribeMessage();
      monitoringSocket.disconnect();
    };
  }, [applyPingResult, setConnectionStatus]);
}
