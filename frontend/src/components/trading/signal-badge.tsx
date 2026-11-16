"use client";

import { Ban, CircleCheck, Eye, LogOut, ShieldCheck, type LucideIcon } from "lucide-react";
import { SIGNAL_STATES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { SignalState } from "@/types";
import { Tooltip } from "@/components/ui/tooltip";

/**
 * Each signal state has a distinct shape + colour + icon + word so states
 * are distinguishable without relying on colour (UX-02, design-standards §6).
 * A tooltip always explains the state — there is never a bare BUY/SELL label.
 *
 * Shapes: BUY WATCH dashed outline · ENTRY CONFIRMED solid fill · HOLD soft
 * chip · EXIT soft chip + solid border · NO TRADE plain outline.
 */
const STYLE: Record<SignalState, { icon: LucideIcon; cls: string }> = {
  "buy-watch": { icon: Eye, cls: "border border-dashed border-warning text-warning" },
  "entry-confirmed": { icon: CircleCheck, cls: "border border-success bg-success text-success-foreground" },
  hold: { icon: ShieldCheck, cls: "border border-transparent bg-info/10 text-info" },
  exit: { icon: LogOut, cls: "border border-destructive/50 bg-destructive/10 text-destructive" },
  "no-trade": { icon: Ban, cls: "border border-input text-muted-foreground" },
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
        "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full font-semibold tracking-wide",
        size === "sm" ? "h-5 px-2 text-2xs" : "h-6 px-2.5 text-xs",
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
      <span tabIndex={0} className="inline-flex rounded-full">
        {badge}
      </span>
    </Tooltip>
  );
}

/** Full-width explanation block used on analysis and plan detail views. */
export function SignalExplainer({ signal, className }: { signal: SignalState; className?: string }) {
  const meta = SIGNAL_STATES[signal];
  return (
    <div className={cn("flex flex-col items-start gap-1", className)}>
      <SignalBadge signal={signal} size="md" explain={false} />
      <p className="text-sm leading-relaxed text-muted-foreground">{meta.description}</p>
    </div>
  );
}
