"use client";

import { useState } from "react";
import { ClipboardPlus } from "lucide-react";
import type { StockAnalysis, Timeframe } from "@/types";
import { DEFAULT_OVERLAYS, PriceChart, type ChartOverlays } from "@/components/charts/price-chart";
import { Badge } from "@/components/data/badge";
import { PriceDisplay } from "@/components/data/price-display";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { AnalysisPanel } from "@/components/trading/analysis-panel";
import { SignalBadge } from "@/components/trading/signal-badge";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { Segmented } from "@/components/ui/segmented";
import { WatchlistToggle } from "@/features/watchlists/watchlist-toggle";
import { ChartLegend, ChartToolbar } from "./chart-toolbar";
import { CreatePlanDialog } from "./create-plan-dialog";
import { SetupEvidence } from "./setup-evidence";

export function AnalysisView({ a }: { a: StockAnalysis }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("1D");
  const [overlays, setOverlays] = useState<ChartOverlays>(DEFAULT_OVERLAYS);
  const [fit, setFit] = useState(0);
  const [planOpen, setPlanOpen] = useState(false);
  const { stock } = a;

  return (
    <div className="mx-auto flex w-full max-w-[1920px] flex-col gap-3 p-3 sm:p-4 lg:gap-4 lg:px-6">
      {/* Header */}
      <header className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-fg">{stock.symbol}</h1>
              <Badge tone="neutral" variant="outline" size="xs">{stock.exchange}</Badge>
              <Badge tone="neutral" size="xs">{stock.sector}</Badge>
              <SignalBadge signal={a.setup.signal} />
            </div>
            <p className="truncate text-xs text-fg-muted">{stock.name}</p>
          </div>
          <div className="flex flex-col">
            <PriceDisplay price={stock.price} change={stock.change} changePct={stock.changePct} size="lg" />
            <span className="text-2xs text-fg-subtle">Latest available close</span>
          </div>
          <SampleDataBadge asOf={a.asOf} />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Segmented
            ariaLabel="Analysis timeframe"
            value="1D"
            onChange={() => undefined}
            options={[
              { value: "1D", label: "Daily" },
              { value: "1W", label: "Weekly", disabled: true },
            ]}
          />
          <WatchlistToggle symbol={stock.symbol} />
          <Button size="sm" variant="primary" onClick={() => setPlanOpen(true)}>
            <ClipboardPlus /> Create trade plan
          </Button>
        </div>
      </header>

      {/* Chart + analysis */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-4 2xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="flex min-w-0 flex-col lg:col-start-1 lg:row-start-1">
          <Panel className="flex flex-col overflow-hidden">
            <ChartToolbar
              timeframe={timeframe}
              onTimeframe={setTimeframe}
              overlays={overlays}
              onToggle={(k) => setOverlays((o) => ({ ...o, [k]: !o[k] }))}
              onFit={() => setFit((n) => n + 1)}
            />
            <div className="h-[380px] sm:h-[460px] lg:h-[calc(100dvh-235px)] lg:min-h-[520px] lg:max-h-[820px]">
              <PriceChart
                candles={a.candles}
                timeframe={timeframe}
                swings={a.swings}
                breaks={a.breaks}
                zones={a.zones}
                events={a.events}
                levels={a.levels}
                overlays={overlays}
                fitSignal={fit}
              />
            </div>
            <ChartLegend />
          </Panel>
        </div>

        {/* Mobile order: chart → verdict → evidence. Desktop: panel spans the right column. */}
        <Panel className="h-fit self-start lg:sticky lg:top-[72px] lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:max-h-[calc(100dvh-88px)] lg:overflow-y-auto">
          <AnalysisPanel a={a} />
        </Panel>

        <div className="min-w-0 lg:col-start-1 lg:row-start-2">
          <SetupEvidence a={a} />
        </div>
      </div>

      <CreatePlanDialog a={a} open={planOpen} onClose={() => setPlanOpen(false)} />
    </div>
  );
}
