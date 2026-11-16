"use client";

import { useMarketSession } from "@/hooks/use-market-session";
import { TONE_FILL, TONE_TEXT, type StatusTone } from "@/lib/colors";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

const META: Record<"open" | "pre-open" | "closed", { label: string; tone: StatusTone }> = {
  open: { label: "Market open", tone: "success" },
  "pre-open": { label: "Pre-open", tone: "warning" },
  closed: { label: "Market closed", tone: "neutral" },
};

/** NSE session indicator based on exchange hours (IST). A status chip: dot + word. */
export function MarketStatus({ className, variant = "pill" }: { className?: string; variant?: "pill" | "inline" }) {
  const session = useMarketSession();
  const meta = session ? META[session] : null;
  return (
    <Tooltip
      side="bottom"
      content="NSE cash session by exchange hours (09:15–15:30 IST, Mon–Fri). Holidays not yet considered. Prices shown are sample data."
    >
      <span
        tabIndex={0}
        className={cn(
          "inline-flex items-center gap-2 whitespace-nowrap text-xs",
          variant === "pill" && "h-7 rounded-full border px-2.5",
          className,
        )}
      >
        <span className={cn("size-2 rounded-full", meta ? TONE_FILL[meta.tone] : "bg-muted")} aria-hidden />
        <span className={cn("font-medium", meta ? TONE_TEXT[meta.tone] : "text-muted-foreground")}>{meta?.label ?? "NSE"}</span>
        {meta && <span className="text-muted-foreground">NSE</span>}
      </span>
    </Tooltip>
  );
}
