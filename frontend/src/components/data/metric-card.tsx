import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  delta?: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "bull" | "bear" | "warn" | "accent";
  className?: string;
}

const TONE = {
  default: "text-fg",
  bull: "text-bull",
  bear: "text-bear",
  warn: "text-warn",
  accent: "text-accent",
};

/** KPI tile. Flat surface with a single focal number. */
export function MetricCard({ label, value, icon: Icon, delta, hint, tone = "default", className }: MetricCardProps) {
  return (
    <div className={cn("flex flex-col gap-2 rounded-md border border-border bg-surface px-4 py-3.5", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-fg-muted">{label}</span>
        {Icon && <Icon className="size-4 text-fg-subtle" aria-hidden />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={cn("tnum text-xl font-semibold tracking-tight", TONE[tone])}>{value}</span>
        {delta}
      </div>
      {hint && <p className="text-2xs text-fg-subtle">{hint}</p>}
    </div>
  );
}
