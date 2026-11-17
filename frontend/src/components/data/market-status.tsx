"use client";

import { formatCountdown, useSessionClock, type SessionPhase } from "@/hooks/use-market-session";
import { TONE_FILL, TONE_TEXT, type StatusTone } from "@/lib/colors";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

const META: Record<SessionPhase, { label: string; tone: StatusTone }> = {
  open: { label: "Market open", tone: "success" },
  "pre-open": { label: "Pre-open", tone: "warning" },
  "after-cutoff": { label: "No new entries", tone: "warning" },
  "exit-window": { label: "Exit window", tone: "destructive" },
  closed: { label: "Market closed", tone: "neutral" },
};

/**
 * NSE session indicator and clock (PRD-07 UX-09): phase word, dot, and the countdown to the next session event
 * (open, entry cutoff, session-end exit, close). Exchange hours only; holidays need the calendar API.
 */
export function MarketStatus({ className, variant = "pill" }: { className?: string; variant?: "pill" | "inline" }) {
  const clock = useSessionClock();
  const meta = clock ? META[clock.phase] : null;
  return (
    <Tooltip
      side="bottom"
      content="NSE cash session by exchange hours (09:15–15:30 IST, Mon–Fri): no new entries after 14:45, open positions flattened from 15:15. Holidays not yet considered. Prices shown are sample data."
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
        {clock?.next ? (
          <span className="tabular-nums text-muted-foreground">
            {clock.next.label.toLowerCase()} in {formatCountdown(clock.next.minutes)}
          </span>
        ) : (
          meta && <span className="text-muted-foreground">NSE</span>
        )}
      </span>
    </Tooltip>
  );
}
