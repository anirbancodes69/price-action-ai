import { ScanSearch } from "lucide-react";
import type { DashboardSummary } from "@/lib/data";
import type { ActivityItem, MarketIndex, RiskToday, ScannerRow, StockAnalysis, TriggerAlert, Watchlist } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ButtonLink } from "@/components/ui/button";
import { Panel, PanelLink } from "@/components/ui/panel";
import { Disclaimer } from "@/components/data/disclaimer";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { Stat, StatGrid } from "@/components/data/stat";
import { SetupCard } from "@/components/trading/setup-card";
import { StockTable } from "@/components/trading/stock-table";
import { MarketPanel } from "./index-strip";
import { RecentActivity, RecentAnalyses, UpcomingTriggers } from "./side-panels";
import { RiskTodayPanel } from "./risk-today";

export interface DashboardData {
  asOf: string;
  indices: MarketIndex[];
  summary: DashboardSummary;
  topSetups: ScannerRow[];
  watchlist: Watchlist;
  watchlistRows: ScannerRow[];
  triggers: TriggerAlert[];
  recentAnalyses: StockAnalysis[];
  activity: ActivityItem[];
  riskToday: RiskToday[];
}

/**
 * Dashboard order (design-standards §10): the figures → what needs the
 * reader (triggers, nearest first) → what they answer for (setups,
 * watchlist) → history (recent analyses, activity). Blocks with nothing to
 * say are left out. Nothing is entered here; every figure links onward.
 */
export function DashboardView({ d }: { d: DashboardData }) {
  return (
    <PageFrame>
      <PageHeader
        title="Dashboard"
        description="Today's session: setups near their trigger, your risk budget and open plans."
        meta={<SampleDataBadge asOf={d.asOf} />}
        actions={
          <>
            <ButtonLink href="/trade-plans" variant="outline">
              Trade plans
            </ButtonLink>
            <ButtonLink href="/market-scanner" variant="primary">
              <ScanSearch /> Open scanner
            </ButtonLink>
          </>
        }
      />

      <StatGrid columns={3} label="Overview figures">
        <Stat
          label="Active setups"
          value={d.summary.activeSetups}
          hint={`Long setups among ${d.summary.stocksScanned} stocks scanned`}
          href="/market-scanner"
        />
        <Stat label="Awaiting confirmation" value={d.summary.awaitingConfirmation} hint="Near trigger, no confirming close yet" href="/market-scanner" />
        <Stat label="Open trade plans" value={d.summary.activeTradePlans} hint="Pending, confirmed or active" href="/trade-plans" />
      </StatGrid>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
        <div className="flex min-w-0 flex-col gap-6">
          {d.triggers.length > 0 && <UpcomingTriggers triggers={d.triggers} />}

          {d.topSetups.length > 0 && (
            <Panel
              title="Top setups"
              hint="Ranked by quality score. A detected setup is not an entry signal."
              footer={<PanelLink href="/market-scanner">All setups in the scanner</PanelLink>}
            >
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
                {d.topSetups.map((row) => (
                  <SetupCard key={row.stock.symbol} row={row} />
                ))}
              </div>
            </Panel>
          )}

          {d.watchlistRows.length > 0 && (
            <Panel title={`Watchlist · ${d.watchlist.name}`} footer={<PanelLink href="/watchlists">Manage watchlists</PanelLink>}>
              <StockTable
                rows={d.watchlistRows}
                limit={5}
                columns={["symbol", "price", "change", "structure", "status", "signal"]}
                caption="Watchlist snapshot"
              />
            </Panel>
          )}
        </div>

        <aside className="flex min-w-0 flex-col gap-4" aria-label="Risk, market and history">
          <RiskTodayPanel books={d.riskToday} />
          <MarketPanel indices={d.indices} />
          {d.recentAnalyses.length > 0 && <RecentAnalyses analyses={d.recentAnalyses} />}
          {d.activity.length > 0 && <RecentActivity items={d.activity} />}
        </aside>
      </div>

      <Disclaimer />
    </PageFrame>
  );
}
