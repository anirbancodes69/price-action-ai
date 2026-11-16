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
    <ol className={cn("no-scrollbar flex items-stretch overflow-x-auto rounded-xl border bg-card", className)} aria-label="From analysis to execution">
      {STAGES.map((s, i) => {
        const on = highlight.includes(s.key);
        const Icon = s.icon;
        return (
          <li key={s.key} className="flex min-w-44 flex-1 items-center">
            <div className={cn("flex flex-1 items-center gap-3 px-4 py-3", on && "bg-accent")} aria-current={on ? "step" : undefined}>
              <Icon className={cn("size-4 shrink-0", on ? "text-foreground" : "text-muted-foreground")} aria-hidden />
              <div className="flex min-w-0 flex-col gap-1">
                <p className={cn("truncate text-sm", on ? "font-medium text-foreground" : "text-muted-foreground")}>{s.label}</p>
                <p className="truncate text-xs text-muted-foreground">{s.detail}</p>
              </div>
            </div>
            {i < STAGES.length - 1 && <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
