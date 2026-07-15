import { cn } from "@/lib/utils";
import { SEVERITY_BG_CLASS, SEVERITY_LABEL, SEVERITY_TEXT_CLASS } from "@/lib/severity";
import type { Severity } from "@/types/ping";

/**
 * The signature element (per the frontend-design brief): a radar-sweep
 * motif under the status word — literal for a tool whose entire job is
 * pinging things. Everything else in the dashboard stays quiet by
 * comparison; this is the one place we spend the "boldness budget."
 */
export function StatusBanner({ severity }: { severity: Severity | null }) {
  const label = severity ? SEVERITY_LABEL[severity] : "Waiting for data…";
  const textClass = severity ? SEVERITY_TEXT_CLASS[severity] : "text-content-muted";

  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-xs uppercase tracking-[0.3em] text-content-muted">
          Internet
        </span>
        <span
          className={cn("font-mono text-4xl font-semibold tracking-wide sm:text-5xl", textClass)}
        >
          {label}
        </span>
      </div>
      <div className="relative h-px w-64 overflow-hidden bg-border sm:w-96">
        {severity && (
          <span
            className={cn("absolute inset-y-0 left-0 w-1/3 animate-sweep", SEVERITY_BG_CLASS[severity])}
            aria-hidden="true"
          />
        )}
      </div>
    </div>
  );
}
