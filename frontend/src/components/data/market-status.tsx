"use client";

import { useMarketSession } from "@/hooks/use-market-session";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

const META = {
  open: { label: "Market open", dot: "bg-bull", ring: "bg-bull/40", text: "text-bull" },
  "pre-open": { label: "Pre-open", dot: "bg-warn", ring: "bg-warn/40", text: "text-warn" },
  closed: { label: "Market closed", dot: "bg-fg-subtle", ring: "", text: "text-fg-muted" },
} as const;

/** NSE session indicator based on exchange hours (IST). */
export function MarketStatus({ className, variant = "pill" }: { className?: string; variant?: "pill" | "inline" }) {
  const session = useMarketSession();
  const meta = session ? META[session] : null;
  return (
    <Tooltip
      side="bottom"
      content="NSE cash session by exchange hours (09:15–15:30 IST, Mon–Fri). Holidays not yet considered. Prices shown are sample data."
    >
      <span
        className={cn(
          "inline-flex items-center gap-2 whitespace-nowrap text-xs",
          variant === "pill" && "h-7 rounded border border-border bg-subtle px-2.5",
          className,
        )}
      >
        <span className="relative flex size-2">
          {session === "open" && meta && (
            <span className={cn("absolute inline-flex size-full animate-ping rounded-full", meta.ring)} />
          )}
          <span className={cn("relative inline-flex size-2 rounded-full", meta?.dot ?? "bg-hover")} />
        </span>
        <span className={cn("font-medium", meta?.text ?? "text-fg-subtle")}>{meta?.label ?? "NSE"}</span>
        <span className="text-fg-subtle">NSE</span>
      </span>
    </Tooltip>
  );
}
