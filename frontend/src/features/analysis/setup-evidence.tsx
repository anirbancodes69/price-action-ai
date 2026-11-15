import { CircleAlert, CircleCheck, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StockAnalysis } from "@/types";
import { Panel, PanelHeader } from "@/components/ui/panel";

/** "Why is this setup being considered?" — evidence for and against. */
export function SetupEvidence({ a }: { a: StockAnalysis }) {
  return (
    <Panel>
      <PanelHeader
        icon={<Lightbulb />}
        title="Why is this setup being considered?"
        description="Observable price-action evidence behind the read — and what argues against it."
      />
      <ul className="grid grid-cols-1 gap-px bg-border md:grid-cols-2">
        {a.evidence.map((e) => {
          const ok = e.tone === "supporting";
          const Icon = ok ? CircleCheck : CircleAlert;
          return (
            <li key={e.title} className="flex gap-3 bg-surface px-4 py-3.5">
              <Icon className={cn("mt-0.5 size-4 shrink-0", ok ? "text-bull" : "text-warn")} aria-hidden />
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-fg">
                  {e.title}
                  <span className="sr-only">{ok ? " (supporting)" : " (caution)"}</span>
                </p>
                <p className="mt-0.5 text-xs leading-relaxed text-fg-muted">{e.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
