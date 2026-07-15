import { useShallow } from "zustand/react/shallow";

import { ConnectionIndicator } from "@/components/dashboard/ConnectionIndicator";
import { PingChart } from "@/components/dashboard/PingChart";
import { StatusBanner } from "@/components/dashboard/StatusBanner";
import { TargetCard } from "@/components/dashboard/TargetCard";
import { usePingMonitoring } from "@/hooks/usePingMonitoring";
import { usePingStore } from "@/store/pingStore";
import { worstSeverity } from "@/types/ping";

export function Dashboard() {
  usePingMonitoring();

  const connectionStatus = usePingStore((state) => state.connectionStatus);
  // useShallow: without it, this selector returns a brand-new array
  // reference on every store update (even unrelated ones), which
  // React 18's useSyncExternalStore treats as "the snapshot changed
  // again," causing an infinite re-render loop. useShallow compares
  // the resulting array's contents instead of its reference.
  const targets = usePingStore(useShallow((state) => Object.values(state.targets)));

  const overallSeverity = worstSeverity(targets.map((t) => t.severity));

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <header className="flex items-center justify-between">
        <span className="font-mono text-sm font-semibold tracking-[0.2em] text-content">
          NETMON
        </span>
        <ConnectionIndicator status={connectionStatus} />
      </header>

      <StatusBanner severity={overallSeverity} />

      {targets.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border py-16 text-center text-sm text-content-muted">
          No ping data yet. The ping monitor writes its first reading within a few seconds of
          startup.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {targets.map((target) => (
              <TargetCard key={target.target} state={target} />
            ))}
          </div>

          <div className="mt-4">
            <PingChart targets={targets} />
          </div>
        </>
      )}
    </div>
  );
}
