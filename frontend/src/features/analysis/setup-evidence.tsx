import { CircleAlert, CircleCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StockAnalysis } from "@/types";
import { Panel } from "@/components/ui/panel";

/** "Why is this setup being considered?" — evidence for and against, as fill tiles in one boxed panel. */
export function SetupEvidence({ a }: { a: StockAnalysis }) {
  const supporting = a.evidence.filter((e) => e.tone === "supporting").length;
  return (
    <Panel
      boxed
      title="Why this setup"
      meta={
        <span className="text-xs text-muted-foreground">
          {supporting} supporting · {a.evidence.length - supporting} caution
        </span>
      }
      hint="Observable price-action evidence behind the read, and what argues against it."
    >
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {a.evidence.map((e) => {
          const ok = e.tone === "supporting";
          const Icon = ok ? CircleCheck : CircleAlert;
          return (
            <li key={e.title} className="flex gap-3 rounded-lg bg-muted/55 px-4 py-3">
              <Icon className={cn("mt-0.5 size-4 shrink-0", ok ? "text-success" : "text-warning")} aria-hidden />
              <div className="flex min-w-0 flex-col gap-1">
                <p className="text-sm font-medium text-foreground">
                  {e.title}
                  <span className="sr-only">{ok ? " (supporting)" : " (caution)"}</span>
                </p>
                <p className="text-sm leading-relaxed text-muted-foreground">{e.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}
