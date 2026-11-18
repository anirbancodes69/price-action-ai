import { Radio } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Marker for data from a real provider (PERSONAL or LICENSED mode, ADR-011). It states the mode and the bar time:
 * the data is closed-bar analysis, not a tick feed. DEMO data uses `SampleDataBadge` instead and is never styled as live.
 */
export function LiveDataBadge({ mode, asOf, className }: { mode: "PERSONAL" | "LICENSED"; asOf?: string | null; className?: string }) {
  return (
    <span
      className={cn("inline-flex h-5 shrink-0 items-center gap-1 whitespace-nowrap rounded-full bg-info/10 px-2 text-2xs font-medium text-info", className)}
      title="Analysis of closed 5-minute bars from your connected market-data source."
    >
      <Radio className="size-3" aria-hidden />
      {mode === "PERSONAL" ? "Your data" : "Licensed data"}
      {asOf && <span className="font-normal tabular-nums">· as of {formatDateTime(asOf)}</span>}
    </span>
  );
}
