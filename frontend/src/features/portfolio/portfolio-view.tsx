"use client";

import { useState } from "react";
import Link from "next/link";
import { Banknote, PieChart, Receipt, ShieldAlert, TrendingUp, Wallet } from "lucide-react";
import { formatDateTime, formatInr, formatInt, formatLakhCrore, formatPct, formatPrice, formatSignedInr } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AllocationSlice, ExecutedOrder, Holding, PortfolioSummary } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Tabs } from "@/components/ui/tabs";
import { DataTable, type Column } from "@/components/data/data-table";
import { MetricCard } from "@/components/data/metric-card";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { Badge } from "@/components/data/badge";
import { LifecycleStrip } from "@/components/trading/lifecycle-strip";
import { SignalBadge } from "@/components/trading/signal-badge";

const SLICE_COLORS = ["bg-accent", "bg-info", "bg-bull", "bg-warn", "bg-bear", "bg-accent-strong", "bg-fg-subtle"];

interface PortfolioViewProps {
  holdings: Holding[];
  summary: PortfolioSummary;
  allocation: AllocationSlice[];
  orders: ExecutedOrder[];
  asOf: string;
}

export function PortfolioView({ holdings, summary, allocation, orders, asOf }: PortfolioViewProps) {
  const [tab, setTab] = useState<"positions" | "holdings" | "orders">("positions");
  const positions = holdings.filter((h) => h.planId);
  const totalAlloc = allocation.reduce((a, s) => a + s.value, 0);
  const pnlPct = (summary.unrealizedPnl / summary.invested) * 100;

  const columns: Column<Holding>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sticky: true,
      sortValue: (h) => h.symbol,
      render: (h) => (
        <Link href={`/analysis/${h.symbol}`} className="flex flex-col leading-tight">
          <span className="text-[13px] font-semibold text-fg hover:text-accent">{h.symbol}</span>
          <span className="text-2xs text-fg-subtle">{h.planId ? `Plan ${h.planId}` : "No linked plan"}</span>
        </Link>
      ),
    },
    { key: "qty", header: "Qty", align: "right", sortValue: (h) => h.quantity, render: (h) => formatInt(h.quantity) },
    { key: "avg", header: "Avg price", align: "right", hideBelow: "sm", sortValue: (h) => h.avgPrice, render: (h) => formatPrice(h.avgPrice) },
    { key: "ltp", header: "Last close", align: "right", sortValue: (h) => h.ltp, render: (h) => <span className="text-fg">{formatPrice(h.ltp)}</span> },
    {
      key: "pnl",
      header: "Unrealized P&L",
      align: "right",
      sortValue: (h) => (h.ltp - h.avgPrice) * h.quantity,
      render: (h) => {
        const pnl = (h.ltp - h.avgPrice) * h.quantity;
        const pct = ((h.ltp - h.avgPrice) / h.avgPrice) * 100;
        return (
          <span className={cn("flex flex-col leading-tight", pnl >= 0 ? "text-bull" : "text-bear")}>
            <span>{formatSignedInr(pnl, { decimals: false })}</span>
            <span className="text-2xs opacity-80">{formatPct(pct)}</span>
          </span>
        );
      },
    },
    {
      key: "stop",
      header: "Stop",
      align: "right",
      hideBelow: "md",
      sortValue: (h) => h.stopLoss ?? 0,
      render: (h) => (h.stopLoss ? <span className="text-bear">{formatPrice(h.stopLoss)}</span> : <span className="text-warn">No stop</span>),
    },
    {
      key: "risk",
      header: "Risk to stop",
      align: "right",
      hideBelow: "2xl",
      sortValue: (h) => (h.stopLoss ? (h.ltp - h.stopLoss) * h.quantity : Infinity),
      render: (h) => (h.stopLoss ? formatInr(Math.max(0, h.ltp - h.stopLoss) * h.quantity, { decimals: false }) : "—"),
    },
    { key: "signal", header: "Signal", hideBelow: "md", render: (h) => <SignalBadge signal={h.signal} /> },
  ];

  const orderCols: Column<ExecutedOrder>[] = [
    { key: "id", header: "Order", render: (o) => <span className="tnum text-fg">{o.id}</span> },
    { key: "symbol", header: "Symbol", sortValue: (o) => o.symbol, render: (o) => <span className="font-semibold text-fg">{o.symbol}</span> },
    { key: "side", header: "Side", render: (o) => <Badge tone={o.side === "BUY" ? "bull" : "bear"} variant="outline">{o.side} · executed</Badge> },
    { key: "qty", header: "Qty", align: "right", render: (o) => formatInt(o.quantity) },
    { key: "price", header: "Fill price", align: "right", render: (o) => formatPrice(o.price) },
    { key: "plan", header: "Plan", hideBelow: "sm", render: (o) => <span className="text-fg-muted">{o.planId ?? "—"}</span> },
    { key: "at", header: "Executed", hideBelow: "md", sortValue: (o) => o.executedAt, render: (o) => <span className="text-fg-muted">{formatDateTime(o.executedAt)}</span> },
  ];

  const exposure = holdings
    .map((h) => ({ h, risk: h.stopLoss ? Math.max(0, h.ltp - h.stopLoss) * h.quantity : null }))
    .sort((a, b) => (b.risk ?? Infinity) - (a.risk ?? Infinity));

  return (
    <PageContainer>
      <PageHeader
        title="Portfolio"
        description="Executed positions and holdings. Values are sample data; no broker is connected."
        meta={<SampleDataBadge asOf={asOf} />}
      />

      <LifecycleStrip highlight={["order", "position"]} />

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <MetricCard label="Capital" value={formatLakhCrore(summary.capital)} icon={Wallet} />
        <MetricCard label="Invested" value={formatLakhCrore(summary.invested)} icon={Banknote} hint={`${formatPct((summary.invested / summary.capital) * 100, { signed: false, decimals: 1 })} deployed`} />
        <MetricCard label="Cash" value={formatLakhCrore(summary.cash)} icon={PieChart} />
        <MetricCard
          label="Unrealized P&L"
          value={formatSignedInr(summary.unrealizedPnl, { decimals: false })}
          tone={summary.unrealizedPnl >= 0 ? "bull" : "bear"}
          icon={TrendingUp}
          hint={formatPct(pnlPct)}
        />
        <MetricCard label="Realized P&L" value={formatSignedInr(summary.realizedPnl, { decimals: false })} tone={summary.realizedPnl >= 0 ? "bull" : "bear"} hint="From closed journal trades" />
        <MetricCard
          label="Open risk to stops"
          value={formatInr(summary.openRisk, { decimals: false })}
          tone="warn"
          icon={ShieldAlert}
          hint={`${formatPct((summary.openRisk / summary.capital) * 100, { signed: false })} of capital`}
        />
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_380px] lg:gap-5">
        <Panel className="h-fit min-w-0 overflow-hidden">
          <div className="px-4 pt-2">
            <Tabs
              ariaLabel="Portfolio view"
              value={tab}
              onChange={setTab}
              items={[
                { value: "positions", label: "Open positions", count: positions.length },
                { value: "holdings", label: "All holdings", count: holdings.length },
                { value: "orders", label: "Executed orders", count: orders.length },
              ]}
            />
          </div>
          {tab === "orders" ? (
            <DataTable columns={orderCols} rows={orders} rowKey={(o) => o.id} caption="Executed orders" />
          ) : (
            <DataTable
              columns={columns}
              rows={tab === "positions" ? positions : holdings}
              rowKey={(h) => h.symbol}
              initialSort={{ key: "pnl", dir: "desc" }}
              caption={tab === "positions" ? "Open positions" : "Holdings"}
            />
          )}
          <p className="flex items-center gap-1.5 border-t border-border px-4 py-2 text-2xs text-fg-subtle">
            <Receipt className="size-3.5" aria-hidden /> Rows on this page represent executed trades, not proposed plans.
          </p>
        </Panel>

        <div className="flex min-w-0 flex-col gap-4 lg:gap-5">
          <Panel>
            <PanelHeader title="Capital allocation" description="By sector, at last close" icon={<PieChart />} />
            <div className="p-4">
              <div className="flex h-2.5 overflow-hidden rounded-sm" role="img" aria-label="Capital allocation by sector">
                {allocation.map((s, i) => (
                  <span key={s.label} className={cn("h-full", SLICE_COLORS[i % SLICE_COLORS.length])} style={{ width: `${(s.value / totalAlloc) * 100}%` }} />
                ))}
              </div>
              <ul className="tnum mt-4 flex flex-col gap-2 text-xs">
                {allocation.map((s, i) => (
                  <li key={s.label} className="flex items-center gap-2">
                    <span className={cn("size-2 rounded-sm", SLICE_COLORS[i % SLICE_COLORS.length])} aria-hidden />
                    <span className="flex-1 text-fg-muted">{s.label}</span>
                    <span className="text-fg">{formatLakhCrore(s.value)}</span>
                    <span className="w-12 text-right text-fg-subtle">{((s.value / totalAlloc) * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Risk exposure" description={`Max risk per trade: ${summary.maxRiskPerTradePct}% of capital`} icon={<ShieldAlert />} />
            <ul className="flex flex-col gap-3 p-4">
              {exposure.map(({ h, risk }) => {
                const pct = risk === null ? null : (risk / summary.capital) * 100;
                const over = pct !== null && pct > summary.maxRiskPerTradePct;
                return (
                  <li key={h.symbol}>
                    <div className="tnum flex items-center justify-between text-xs">
                      <span className="font-medium text-fg">{h.symbol}</span>
                      <span className={cn(pct === null ? "text-warn" : over ? "text-bear" : "text-fg-muted")}>
                        {pct === null ? "No stop set" : `${formatInr(risk ?? 0, { decimals: false })} · ${pct.toFixed(2)}%`}
                      </span>
                    </div>
                    <span className="mt-1 block h-1 overflow-hidden rounded-full bg-hover">
                      <span
                        className={cn("block h-full rounded-full", pct === null ? "bg-warn" : over ? "bg-bear" : "bg-accent")}
                        style={{ width: `${pct === null ? 100 : Math.min(100, (pct / (summary.maxRiskPerTradePct * 1.5)) * 100)}%` }}
                      />
                    </span>
                  </li>
                );
              })}
            </ul>
          </Panel>
        </div>
      </div>
    </PageContainer>
  );
}
