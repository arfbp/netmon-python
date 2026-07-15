import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { SEVERITY_BORDER_CLASS } from "@/lib/severity";
import { cn } from "@/lib/utils";
import type { TargetState } from "@/store/pingStore";

function formatLatency(ms: number | null): string {
  if (ms === null) return "—";
  return ms < 10 ? ms.toFixed(2) : ms.toFixed(1);
}

export function TargetCard({ state }: { state: TargetState }) {
  const isTimeout = state.isTimeout;

  return (
    <Card className={cn("border-l-4", SEVERITY_BORDER_CLASS[state.severity])}>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{state.target}</CardTitle>
        <SeverityBadge severity={state.severity} />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-1">
          <span className="font-mono text-4xl font-semibold text-content tabular-nums">
            {isTimeout ? "TIMEOUT" : formatLatency(state.latencyMs)}
          </span>
          {!isTimeout && <span className="font-mono text-sm text-content-muted">ms</span>}
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-content-muted">
          <div className="flex justify-between">
            <dt>Jitter</dt>
            <dd className="font-mono tabular-nums">
              {state.jitterMs === null ? "—" : `${state.jitterMs.toFixed(1)} ms`}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt>Avg</dt>
            <dd className="font-mono tabular-nums">
              {state.rollingAvgMs === null ? "—" : `${state.rollingAvgMs.toFixed(1)} ms`}
            </dd>
          </div>
          <div className="col-span-2 flex justify-between">
            <dt>Packet loss</dt>
            <dd className="font-mono tabular-nums">{state.packetLossPct.toFixed(0)}%</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
