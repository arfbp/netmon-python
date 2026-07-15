import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";
import { SEVERITY_BG_CLASS, SEVERITY_LABEL } from "@/lib/severity";
import type { Severity } from "@/types/ping";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        className,
      )}
      {...props}
    />
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge className={cn(SEVERITY_BG_CLASS[severity], "text-bg")}>
      {SEVERITY_LABEL[severity]}
    </Badge>
  );
}
