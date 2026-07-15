import { cn } from "@/lib/utils";
import type { ConnectionStatus } from "@/lib/websocket";

const STATUS_CONFIG: Record<
  ConnectionStatus,
  { label: string; dotClass: string; pulse: boolean }
> = {
  connected: { label: "Connected", dotClass: "bg-severity-excellent", pulse: false },
  connecting: { label: "Connecting…", dotClass: "bg-severity-warning", pulse: true },
  disconnected: { label: "Disconnected", dotClass: "bg-severity-critical", pulse: true },
};

export function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <div className="flex items-center gap-2 text-xs text-content-muted">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          config.dotClass,
          config.pulse && "animate-pulse-dot",
        )}
        aria-hidden="true"
      />
      <span>{config.label}</span>
    </div>
  );
}
