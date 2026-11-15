"use client";

import { Ban, CircleCheck, Eye, LogOut, ShieldCheck, type LucideIcon } from "lucide-react";
import { SIGNAL_STATES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { SignalState } from "@/types";
import { Tooltip } from "@/components/ui/tooltip";

/**
 * Each signal state has a distinct shape + colour + icon so states are
 * distinguishable without relying on colour alone. A tooltip always explains
 * what the state means — there is never a bare BUY/SELL label.
 */
const STYLE: Record<SignalState, { icon: LucideIcon; cls: string }> = {
  "buy-watch": { icon: Eye, cls: "border border-dashed border-warn/60 text-warn bg-warn/5" },
  "entry-confirmed": { icon: CircleCheck, cls: "bg-bull-strong text-white border border-bull-strong" },
  hold: { icon: ShieldCheck, cls: "border border-info/40 bg-info/10 text-info" },
  exit: { icon: LogOut, cls: "border border-bear/50 bg-bear/12 text-bear" },
  "no-trade": { icon: Ban, cls: "border border-border-strong text-fg-muted bg-transparent" },
};

interface SignalBadgeProps {
  signal: SignalState;
  size?: "sm" | "md";
  explain?: boolean;
  className?: string;
}

export function SignalBadge({ signal, size = "sm", explain = true, className }: SignalBadgeProps) {
  const meta = SIGNAL_STATES[signal];
  const { icon: Icon, cls } = STYLE[signal];
  const badge = (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-sm font-semibold tracking-wide",
        size === "sm" ? "h-5 px-1.5 text-[10px]" : "h-6 px-2 text-2xs",
        cls,
        className,
      )}
      aria-label={`${meta.label}: ${meta.description}`}
    >
      <Icon className={size === "sm" ? "size-3" : "size-3.5"} aria-hidden />
      {meta.label}
    </span>
  );
  if (!explain) return badge;
  return (
    <Tooltip content={meta.description} side="top">
      <span tabIndex={0} className="inline-flex rounded-sm">
        {badge}
      </span>
    </Tooltip>
  );
}

/** Full-width explanation block used on analysis and plan detail views. */
export function SignalExplainer({ signal, className }: { signal: SignalState; className?: string }) {
  const meta = SIGNAL_STATES[signal];
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <SignalBadge signal={signal} size="md" explain={false} />
      <p className="text-xs leading-relaxed text-fg-muted">{meta.description}</p>
    </div>
  );
}
