import { ChevronRight, CircleCheck, ClipboardList, LogOut, Radar, Receipt, Wallet, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type LifecycleStage = "setup" | "trigger" | "plan" | "order" | "position" | "exit";

const STAGES: { key: LifecycleStage; label: string; detail: string; icon: LucideIcon }[] = [
  { key: "setup", label: "Detected setup", detail: "Pattern found by analysis", icon: Radar },
  { key: "trigger", label: "Entry trigger", detail: "Condition met on close", icon: CircleCheck },
  { key: "plan", label: "Proposed plan", detail: "Your levels & size", icon: ClipboardList },
  { key: "order", label: "Executed order", detail: "Filled at broker", icon: Receipt },
  { key: "position", label: "Open position", detail: "Capital at risk", icon: Wallet },
  { key: "exit", label: "Exit condition", detail: "Target, stop or invalidation", icon: LogOut },
];

/**
 * Explains the distinct stages from analysis to execution so a detected
 * setup is never confused with an order or a position.
 */
export function LifecycleStrip({ highlight = [], className }: { highlight?: LifecycleStage[]; className?: string }) {
  return (
    <ol className={cn("no-scrollbar flex items-stretch overflow-x-auto rounded-md border border-border bg-surface", className)} aria-label="From analysis to execution">
      {STAGES.map((s, i) => {
        const on = highlight.includes(s.key);
        const Icon = s.icon;
        return (
          <li key={s.key} className="flex min-w-[150px] flex-1 items-center">
            <div className={cn("flex flex-1 items-center gap-2.5 px-3 py-2.5", on && "bg-accent/8")}>
              <Icon className={cn("size-4 shrink-0", on ? "text-accent" : "text-fg-subtle")} aria-hidden />
              <div className="min-w-0">
                <p className={cn("truncate text-xs font-medium", on ? "text-fg" : "text-fg-muted")}>{s.label}</p>
                <p className="truncate text-2xs text-fg-subtle">{s.detail}</p>
              </div>
            </div>
            {i < STAGES.length - 1 && <ChevronRight className="size-3.5 shrink-0 text-border-strong" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
