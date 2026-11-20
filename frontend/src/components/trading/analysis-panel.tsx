import type { ReactNode } from "react";
import { CircleDot, OctagonX } from "lucide-react";
import { scoreTone, TONE_FILL } from "@/lib/colors";
import { formatPrice, formatTime } from "@/lib/format";
import { BIAS, SETUP_STATUS, SETUP_TYPES } from "@/lib/labels";
import { cn } from "@/lib/utils";
import type { SetupStatus, StockAnalysis } from "@/types";
import { Badge } from "@/components/data/badge";
import { Disclaimer } from "@/components/data/disclaimer";
import { Eyebrow } from "@/components/data/stat";
import { RowList } from "@/components/ui/panel";
import { MarketStructureBadge } from "./market-structure-badge";
import { PriceLevelIndicator } from "./price-level-indicator";
import { QualityScoreRing } from "./quality-score";
import { RiskRewardDisplay } from "./risk-reward-display";
import { SignalExplainer } from "./signal-badge";

/** A rule-separated block inside the analysis card (card content, not a nested panel). */
function Block({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-b px-5 py-4 last:border-0">
      <div className="flex min-h-5 items-center justify-between gap-2">
        <Eyebrow as="h3">{title}</Eyebrow>
        {aside}
      </div>
      {children}
    </section>
  );
}

const LIFECYCLE: SetupStatus[] = ["detected", "awaiting-confirmation", "entry-confirmed"];
const LIFECYCLE_SHORT: Record<string, string> = { detected: "Forming", "awaiting-confirmation": "Awaiting", "entry-confirmed": "Confirmed" };

/** Forming → Awaiting confirmation → Entry confirmed (or Invalidated or Expired). An ordered state: the step ramp. */
function SetupLifecycle({ status }: { status: SetupStatus }) {
  if (status === "invalidated") {
    return (
      <Badge tone="destructive" dot>
        Invalidated
      </Badge>
    );
  }
  if (status === "expired") {
    return (
      <Badge tone="neutral" dot>
        Expired
      </Badge>
    );
  }
  const idx = LIFECYCLE.indexOf(status);
  return (
    <ol className="flex items-center gap-1" aria-label={`Setup lifecycle: ${SETUP_STATUS[status].label}`}>
      {LIFECYCLE.map((s, i) => {
        const done = i <= idx;
        return (
          <li key={s} className="flex min-w-0 flex-1 flex-col gap-1" aria-current={i === idx ? "step" : undefined}>
            <span className={cn("h-1 rounded-full", done ? TONE_FILL[SETUP_STATUS[s].tone] : "bg-muted")} />
            <span className={cn("truncate text-2xs", i === idx ? "font-medium text-foreground" : "text-muted-foreground")}>{LIFECYCLE_SHORT[s]}</span>
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
      <Block title="Active setup" aside={<span className="text-xs text-muted-foreground">{SETUP_TYPES[a.setup.type].label}</span>}>
        <SignalExplainer signal={a.setup.signal} />
        {a.signalAt && (
          <p className="text-xs tabular-nums text-muted-foreground">
            Signal at the {formatTime(a.signalAt)} close
            {a.validUntil && <> · valid until {formatTime(a.validUntil)} IST</>}
          </p>
        )}
        <p className="text-sm leading-relaxed text-foreground">{a.setup.headline}</p>
        <SetupLifecycle status={a.setup.status} />
      </Block>

      <Block title="Market structure">
        <dl className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 text-xs">
          <dt className="text-muted-foreground">15m context</dt>
          <dd>
            <MarketStructureBadge structure={a.htfStructure} />
          </dd>
          <dt className="text-muted-foreground">5m structure</dt>
          <dd>
            <MarketStructureBadge structure={a.structure} />
          </dd>
        </dl>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={bias.tone} variant="outline">
            {bias.label} bias
          </Badge>
        </div>
        <p className="text-sm leading-relaxed text-muted-foreground">{a.trendSummary}</p>
        <div className="flex flex-wrap gap-1" aria-label="Recent swing sequence">
          {a.swings.slice(-6).map((s) => (
            <span
              key={s.time}
              className={cn(
                "rounded-full px-2 py-0.5 text-2xs font-semibold tabular-nums",
                s.label === "HH" || s.label === "HL" ? "bg-bull/10 text-bull" : "bg-bear/10 text-bear",
              )}
              title={`${s.label} at ${formatPrice(s.price)} on ${s.time}`}
            >
              {s.label}
            </span>
          ))}
        </div>
      </Block>

      <Block title="Price-action quality">
        <div className="flex items-start gap-4">
          <QualityScoreRing score={a.qualityScore} />
          <ul className="flex min-w-0 flex-1 flex-col gap-2">
            {a.qualityFactors.map((f) => (
              <li key={f.label} title={f.note} className="flex flex-col gap-1">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="truncate text-muted-foreground">{f.label}</span>
                  <span className="tabular-nums text-foreground">{f.score}</span>
                </div>
                <span className="block h-1 overflow-hidden rounded-full bg-muted" aria-hidden>
                  <span className={cn("block h-full rounded-full", TONE_FILL[scoreTone(f.score)])} style={{ width: `${f.score}%` }} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      </Block>

      <Block
        title="Trade levels"
        aside={
          isReference ? (
            <Badge tone="neutral" variant="outline">
              Reference only
            </Badge>
          ) : (
            <Badge tone="info" variant="outline">
              Proposed
            </Badge>
          )
        }
      >
        {a.levels ? (
          <>
            <RiskRewardDisplay levels={a.levels} direction={a.setup.direction} />
            <PriceLevelIndicator price={a.stock.price} levels={a.levels} />
            <p className="text-xs text-muted-foreground">Levels describe a potential plan. Nothing here is an order.</p>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">No setup with levels right now. No-trade is a valid outcome.</p>
        )}
      </Block>

      <Block title="Entry conditions">
        <ul className="flex flex-col gap-2">
          {a.entryConditions.map((c) => (
            <li key={c} className="flex gap-2 text-sm leading-relaxed text-muted-foreground">
              <CircleDot className="mt-1 size-3.5 shrink-0 text-chart-entry" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
      </Block>

      <Block title="Invalidation">
        <ul className="flex flex-col gap-2">
          {a.invalidation.map((c) => (
            <li key={c} className="flex gap-2 text-sm leading-relaxed text-muted-foreground">
              <OctagonX className="mt-1 size-3.5 shrink-0 text-destructive" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
      </Block>

      <Block title="Session" aside={<span className="text-xs tabular-nums text-muted-foreground">cutoff {formatTime(a.session.entryCutoffAt)} · exit {formatTime(a.session.sessionEndExitAt)}</span>}>
        <RowList className="text-sm tabular-nums">
          {[
            ["Previous-day high", formatPrice(a.session.pdh)],
            ["Previous-day low", formatPrice(a.session.pdl)],
            ["Previous-day close", formatPrice(a.session.pdc)],
            [
              "Opening range",
              a.session.orHigh !== null && a.session.orLow !== null ? `${formatPrice(a.session.orLow)}–${formatPrice(a.session.orHigh)}` : "Forming",
            ],
            ["Session range", `${formatPrice(a.session.sessionLow)}–${formatPrice(a.session.sessionHigh)}`],
          ].map(([label, value]) => (
            <li key={label} className="flex items-center justify-between gap-2 px-3 py-2">
              <span className="truncate text-muted-foreground">{label}</span>
              <span className="shrink-0 text-foreground">{value}</span>
            </li>
          ))}
        </RowList>
        <p className="text-xs text-muted-foreground">No new entries after the cutoff; open positions are flattened by the session-end exit.</p>
      </Block>

      <Block title="Key support & resistance">
        <RowList className="text-sm tabular-nums">
          {[...resistances, ...supports].map((z) => (
            <li key={z.id} className="flex items-center justify-between gap-2 px-3 py-2">
              <span className="flex min-w-0 items-center gap-2">
                <span className={cn("h-3 w-1 shrink-0 rounded-full", z.kind === "support" ? "bg-bull" : "bg-bear")} aria-hidden />
                <span className="sr-only">{z.kind === "support" ? "Support" : "Resistance"}: </span>
                <span className="truncate text-muted-foreground">{z.label}</span>
              </span>
              <span className="shrink-0 text-foreground">
                {formatPrice(z.low)}–{formatPrice(z.high)}
              </span>
            </li>
          ))}
        </RowList>
      </Block>

      <div className="px-5 py-4">
        <Disclaimer />
      </div>
    </div>
  );
}
