import type { ReactNode } from "react";
import { CircleDot, OctagonX } from "lucide-react";
import { formatPrice } from "@/lib/format";
import { BIAS, SETUP_STATUS, SETUP_TYPES, TONE_CLASSES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { SetupStatus, StockAnalysis } from "@/types";
import { Badge } from "@/components/data/badge";
import { Disclaimer } from "@/components/data/disclaimer";
import { MarketStructureBadge } from "./market-structure-badge";
import { PriceLevelIndicator } from "./price-level-indicator";
import { QualityScoreRing } from "./quality-score";
import { RiskRewardDisplay } from "./risk-reward-display";
import { SignalExplainer } from "./signal-badge";

function Section({ title, children, aside, className }: { title: string; children: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <section className={cn("border-b border-border px-4 py-4 last:border-0", className)}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-2xs font-semibold uppercase tracking-wider text-fg-subtle">{title}</h3>
        {aside}
      </div>
      {children}
    </section>
  );
}

const LIFECYCLE: SetupStatus[] = ["detected", "awaiting-confirmation", "entry-confirmed"];
const LIFECYCLE_SHORT: Record<string, string> = { detected: "Detected", "awaiting-confirmation": "Awaiting", "entry-confirmed": "Confirmed" };

/** Detected → Awaiting confirmation → Entry confirmed (or Invalidated). */
function SetupLifecycle({ status }: { status: SetupStatus }) {
  if (status === "invalidated") {
    return <Badge tone="bear" dot>Invalidated</Badge>;
  }
  const idx = LIFECYCLE.indexOf(status);
  return (
    <ol className="flex items-center gap-1" aria-label="Setup lifecycle">
      {LIFECYCLE.map((s, i) => {
        const done = i <= idx;
        return (
          <li key={s} className="flex min-w-0 flex-1 flex-col gap-1">
            <span className={cn("h-1 rounded-full", done ? TONE_CLASSES[SETUP_STATUS[s].tone].dot : "bg-hover")} />
            <span className={cn("truncate text-[10px]", i === idx ? "font-medium text-fg" : "text-fg-subtle")}>{LIFECYCLE_SHORT[s]}</span>
          </li>
        );
      })}
    </ol>
  );
}

/** Right-hand analysis column on the Stock Analysis page. */
export function AnalysisPanel({ a, className }: { a: StockAnalysis; className?: string }) {
  const bias = BIAS[a.bias];
  const supports = a.zones.filter((z) => z.kind === "support").sort((x, y) => y.high - x.high);
  const resistances = a.zones.filter((z) => z.kind === "resistance").sort((x, y) => x.low - y.low);
  const isReference = a.setup.direction === "short" || a.setup.signal === "no-trade";

  return (
    <div className={cn("flex flex-col", className)}>
      <Section title="Active setup" aside={<span className="text-2xs text-fg-muted">{SETUP_TYPES[a.setup.type].label}</span>}>
        <SignalExplainer signal={a.setup.signal} />
        <p className="mt-3 text-[13px] leading-relaxed text-fg">{a.setup.headline}</p>
        <div className="mt-3">
          <SetupLifecycle status={a.setup.status} />
        </div>
      </Section>

      <Section title="Market structure">
        <div className="flex flex-wrap items-center gap-2">
          <MarketStructureBadge structure={a.structure} />
          <Badge tone={bias.tone} variant="outline">{bias.label} bias</Badge>
        </div>
        <p className="mt-2.5 text-xs leading-relaxed text-fg-muted">{a.trendSummary}</p>
        <div className="mt-2.5 flex flex-wrap gap-1" aria-label="Recent swing sequence">
          {a.swings.slice(-6).map((s) => (
            <span
              key={s.time}
              className={cn(
                "tnum rounded-sm px-1.5 py-0.5 text-[10px] font-semibold",
                s.label === "HH" || s.label === "HL" ? "bg-bull/10 text-bull" : "bg-bear/10 text-bear",
              )}
              title={`${s.label} at ${formatPrice(s.price)} on ${s.time}`}
            >
              {s.label}
            </span>
          ))}
        </div>
      </Section>

      <Section title="Price-action quality">
        <div className="flex items-start gap-4">
          <QualityScoreRing score={a.qualityScore} />
          <ul className="flex min-w-0 flex-1 flex-col gap-1.5">
            {a.qualityFactors.map((f) => (
              <li key={f.label} title={f.note}>
                <div className="flex items-center justify-between text-2xs">
                  <span className="truncate text-fg-muted">{f.label}</span>
                  <span className="tnum text-fg-subtle">{f.score}</span>
                </div>
                <span className="mt-0.5 block h-1 overflow-hidden rounded-full bg-hover">
                  <span
                    className={cn("block h-full rounded-full", f.score >= 75 ? "bg-bull" : f.score >= 55 ? "bg-warn" : "bg-bear")}
                    style={{ width: `${f.score}%` }}
                  />
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section
        title="Trade levels"
        aside={isReference ? <Badge tone="neutral" variant="outline" size="xs">Reference only</Badge> : <Badge tone="accent" variant="outline" size="xs">Proposed</Badge>}
      >
        <RiskRewardDisplay levels={a.levels} direction={a.setup.direction} />
        <PriceLevelIndicator price={a.stock.price} levels={a.levels} className="mt-2" />
        <p className="text-2xs text-fg-subtle">Levels describe a potential plan. Nothing here is an order.</p>
      </Section>

      <Section title="Entry conditions">
        <ul className="flex flex-col gap-2">
          {a.entryConditions.map((c) => (
            <li key={c} className="flex gap-2 text-xs leading-relaxed text-fg-muted">
              <CircleDot className="mt-0.5 size-3.5 shrink-0 text-accent" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Invalidation">
        <ul className="flex flex-col gap-2">
          {a.invalidation.map((c) => (
            <li key={c} className="flex gap-2 text-xs leading-relaxed text-fg-muted">
              <OctagonX className="mt-0.5 size-3.5 shrink-0 text-bear" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Key support & resistance">
        <ul className="tnum flex flex-col divide-y divide-border/60 text-xs">
          {[...resistances, ...supports].map((z) => (
            <li key={z.id} className="flex items-center justify-between gap-2 py-1.5">
              <span className="flex min-w-0 items-center gap-2">
                <span className={cn("h-3 w-1 shrink-0 rounded-full", z.kind === "support" ? "bg-bull" : "bg-bear")} aria-hidden />
                <span className="truncate text-fg-muted">{z.label}</span>
              </span>
              <span className="shrink-0 text-fg">
                {formatPrice(z.low)}–{formatPrice(z.high)}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <div className="px-4 py-3">
        <Disclaimer />
      </div>
    </div>
  );
}
