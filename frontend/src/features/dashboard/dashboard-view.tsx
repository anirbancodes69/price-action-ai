import { ArrowRight, CircleDashed, ClipboardList, Hourglass, Radar, ScanSearch, Sparkles, ListChecks } from "lucide-react";
import type { DashboardSummary } from "@/lib/data";
import type { ActivityItem, MarketIndex, ScannerRow, StockAnalysis, TriggerAlert, Watchlist } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { ButtonLink } from "@/components/ui/button";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Disclaimer } from "@/components/data/disclaimer";
import { MetricCard } from "@/components/data/metric-card";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { SetupCard } from "@/components/trading/setup-card";
import { StockTable } from "@/components/trading/stock-table";
import { IndexStrip } from "./index-strip";
import { RecentActivity, RecentAnalyses, UpcomingTriggers } from "./side-panels";

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
}

export function DashboardView({ d }: { d: DashboardData }) {
  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description="Market context, detected setups and your trade plans at a glance."
        meta={<SampleDataBadge asOf={d.asOf} />}
        actions={
          <>
            <ButtonLink href="/market-scanner" size="sm" variant="secondary">
              <ScanSearch /> Open scanner
            </ButtonLink>
            <ButtonLink href="/trade-plans" size="sm" variant="primary">
              <ClipboardList /> Trade plans
            </ButtonLink>
          </>
        }
      />

      <IndexStrip indices={d.indices} />

      <section aria-label="Overview metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Stocks scanned" value={d.summary.stocksScanned} icon={Radar} hint="Sample universe · daily timeframe" />
        <MetricCard label="Active setups" value={d.summary.activeSetups} icon={Sparkles} tone="accent" hint="Long setups detected or confirmed" />
        <MetricCard label="Awaiting confirmation" value={d.summary.awaitingConfirmation} icon={Hourglass} tone="warn" hint="Near trigger, no confirming close yet" />
        <MetricCard label="Active trade plans" value={d.summary.activeTradePlans} icon={CircleDashed} hint="Pending, confirmed or active plans" />
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_360px] lg:gap-5">
        <div className="flex min-w-0 flex-col gap-4 lg:gap-5">
          <Panel>
            <PanelHeader
              title="Top price-action setups"
              description="Ranked by quality score. Detected setups are not entry signals."
              icon={<Sparkles />}
              actions={
                <ButtonLink href="/market-scanner" size="xs" variant="ghost">
                  View all <ArrowRight />
                </ButtonLink>
              }
            />
            <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 2xl:grid-cols-3">
              {d.topSetups.map((row) => (
                <SetupCard key={row.stock.symbol} row={row} />
              ))}
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title={`Watchlist · ${d.watchlist.name}`}
              icon={<ListChecks />}
              actions={
                <ButtonLink href="/watchlists" size="xs" variant="ghost">
                  Manage <ArrowRight />
                </ButtonLink>
              }
            />
            <StockTable
              rows={d.watchlistRows}
              columns={["symbol", "price", "change", "structure", "status", "signal"]}
              caption="Watchlist snapshot"
            />
          </Panel>
        </div>

        <aside className="flex min-w-0 flex-col gap-4 lg:gap-5">
          <UpcomingTriggers triggers={d.triggers} />
          <RecentAnalyses analyses={d.recentAnalyses} />
          <RecentActivity items={d.activity} />
        </aside>
      </div>

      <Disclaimer />
    </PageContainer>
  );
}
