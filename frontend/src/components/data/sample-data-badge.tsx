import { FlaskConical } from "lucide-react";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Mandatory marker on any surface showing sample values. Keeps the demo
 * honest: nothing in Phase 1 is live market data.
 */
export function SampleDataBadge({ asOf, className, compact }: { asOf?: string; className?: string; compact?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-sm border border-warn/25 bg-warn/8 px-1.5 py-0.5 text-2xs font-medium text-warn",
        className,
      )}
      title="Illustrative sample data. Not live or historical market data."
    >
      <FlaskConical className="size-3" aria-hidden />
      {compact ? "Sample" : "Sample data"}
      {asOf && !compact && <span className="font-normal text-warn/80">· {formatDate(asOf)}</span>}
    </span>
  );
}
