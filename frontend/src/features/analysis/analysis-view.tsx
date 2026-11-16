"use client";

import { useState } from "react";
import { ClipboardPlus } from "lucide-react";
import type { StockAnalysis, Timeframe } from "@/types";
import { DEFAULT_OVERLAYS, PriceChart, type ChartOverlays } from "@/components/charts/price-chart";
import { Badge } from "@/components/data/badge";
import { PriceDisplay } from "@/components/data/price-display";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { AnalysisPanel } from "@/components/trading/analysis-panel";
import { SignalBadge } from "@/components/trading/signal-badge";
import { Button } from "@/components/ui/button";
import { WatchlistToggle } from "@/features/watchlists/watchlist-toggle";
import { ChartLegend, ChartToolbar } from "./chart-toolbar";
import { CreatePlanDialog } from "./create-plan-dialog";
import { SetupEvidence } from "./setup-evidence";

/**
 * Stock Analysis workspace (core product surface). Desktop-first: chart and
 * evidence on the left, the verdict card sticky on the right. Mobile order:
 * chart → verdict → evidence.
 */
export function AnalysisView({ a }: { a: StockAnalysis }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("1D");
  const [overlays, setOverlays] = useState<ChartOverlays>(DEFAULT_OVERLAYS);
  const [fit, setFit] = useState(0);
  const [planOpen, setPlanOpen] = useState(false);
  const { stock } = a;
  const reference = a.setup.direction === "short" || a.setup.signal === "no-trade";

  return (
    <PageFrame>
      <PageHeader
        title={stock.symbol}
        description={stock.name}
        meta={
          <>
            <Badge variant="outline">{stock.exchange}</Badge>
            <Badge>{stock.sector}</Badge>
            <SignalBadge signal={a.setup.signal} />
            <SampleDataBadge asOf={a.asOf} />
          </>
        }
        actions={
          <>
            <div className="flex flex-col items-end gap-1 pr-2">
              <PriceDisplay price={stock.price} change={stock.change} changePct={stock.changePct} size="lg" />
              <span className="text-xs text-muted-foreground">Latest available close · daily analysis</span>
            </div>
            <WatchlistToggle symbol={stock.symbol} />
            <Button variant="primary" onClick={() => setPlanOpen(true)} disabled={a.setup.direction === "short"}>
              <ClipboardPlus /> Create trade plan
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem] 2xl:grid-cols-[minmax(0,1fr)_24rem]">
        <section
          aria-label={`${stock.symbol} price chart`}
          data-slot="card"
          className="flex min-w-0 flex-col overflow-hidden rounded-xl border bg-card lg:col-start-1 lg:row-start-1"
        >
          <ChartToolbar
            timeframe={timeframe}
            onTimeframe={setTimeframe}
            overlays={overlays}
            onToggle={(k) => setOverlays((o) => ({ ...o, [k]: !o[k] }))}
            onFit={() => setFit((n) => n + 1)}
          />
          <div className="h-[380px] sm:h-[460px] lg:h-[calc(100dvh-280px)] lg:max-h-[820px] lg:min-h-[520px]">
            <PriceChart
              candles={a.candles}
              timeframe={timeframe}
              swings={a.swings}
              breaks={a.breaks}
              zones={a.zones}
              events={a.events}
              levels={a.levels}
              overlays={overlays}
              referenceLevels={reference}
              fitSignal={fit}
            />
          </div>
          <ChartLegend reference={reference} />
        </section>

        <aside
          aria-label="Analysis verdict"
          data-slot="card"
          className="h-fit self-start rounded-xl border bg-card lg:sticky lg:top-[72px] lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:max-h-[calc(100dvh-88px)] lg:overflow-y-auto"
        >
          <AnalysisPanel a={a} />
        </aside>

        <div className="min-w-0 lg:col-start-1 lg:row-start-2">
          <SetupEvidence a={a} />
        </div>
      </div>

      <CreatePlanDialog a={a} open={planOpen} onClose={() => setPlanOpen(false)} />
    </PageFrame>
  );
}
