import { FlaskConical } from "lucide-react";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Mandatory marker on any surface showing sample values (C-03, ADR-011).
 * A warning chip with an icon and the word "Sample": nothing in Phase 1 is
 * live market data.
 */
export function SampleDataBadge({ asOf, className, compact }: { asOf?: string; className?: string; compact?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 shrink-0 items-center gap-1 whitespace-nowrap rounded-full bg-warning/10 px-2 text-2xs font-medium text-warning",
        className,
      )}
      title="Illustrative sample data. Not live or historical market data."
    >
      <FlaskConical className="size-3" aria-hidden />
      {compact ? "Sample" : "Sample data"}
      {asOf && !compact && <span className="font-normal">· as of {formatDate(asOf)}</span>}
    </span>
  );
}
