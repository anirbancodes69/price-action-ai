"use client";

import { useState } from "react";
import Link from "next/link";
import { Receipt, Wallet } from "lucide-react";
import { CHART_REST, chartSlot } from "@/lib/colors";
import { formatDateTime, formatInr, formatInt, formatLakhCrore, formatPct, formatPrice, formatSignedInr } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AllocationSlice, ExecutedOrder, Holding, PortfolioSummary } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { FilterRow } from "@/components/ui/filter-row";
import { Panel } from "@/components/ui/panel";
import { DataTable, type Column } from "@/components/data/data-table";
import { Empty } from "@/components/data/empty";
import { Stat, StatGrid } from "@/components/data/stat";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { Badge } from "@/components/data/badge";
import { LifecycleStrip } from "@/components/trading/lifecycle-strip";
import { SignalBadge } from "@/components/trading/signal-badge";


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
  const totalAlloc = allocation.reduce((a, s) => a + s.value, 0) || 1;
  // Chart slots in order, never cycled; beyond eight the tail is grouped into "Other" (design-standards §6).
  const grouped = allocation.length > 8;
  const slices = grouped
    ? [...allocation.slice(0, 7), { label: "Other", value: allocation.slice(7).reduce((a, s) => a + s.value, 0) }]
    : allocation;
  const slotFor = (i: number) => (grouped && i === 7 ? CHART_REST : chartSlot(i));
  const pnlPct = (summary.unrealizedPnl / summary.invested) * 100;

  const columns: Column<Holding>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sticky: true,
      grow: true,
      sortValue: (h) => h.symbol,
      render: (h) => (
        <Link href={`/analysis/${h.symbol}`} className="flex flex-col rounded-lg leading-tight">
          <span className="text-sm font-medium text-foreground underline-offset-4 hover:underline">{h.symbol}</span>
          <span className="truncate text-xs text-muted-foreground">{h.planId ? `Plan ${h.planId}` : "No linked plan"}</span>
        </Link>
      ),
    },
    { key: "qty", header: "Qty", align: "right", sortValue: (h) => h.quantity, render: (h) => formatInt(h.quantity) },
    { key: "avg", header: "Avg price", align: "right", hideBelow: "lg", sortValue: (h) => h.avgPrice, render: (h) => formatPrice(h.avgPrice) },
    { key: "ltp", header: "Last close", align: "right", sortValue: (h) => h.ltp, render: (h) => <span className="text-foreground">{formatPrice(h.ltp)}</span> },
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
            <span className="text-xs">{formatPct(pct)}</span>
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
      render: (h) => (h.stopLoss ? <span className="text-bear">{formatPrice(h.stopLoss)}</span> : <Badge tone="warning">No stop</Badge>),
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
    { key: "id", header: "Order", render: (o) => <span className="font-mono text-xs text-foreground">{o.id}</span> },
    { key: "symbol", header: "Symbol", grow: true, sortValue: (o) => o.symbol, render: (o) => <span className="font-medium text-foreground">{o.symbol}</span> },
    { key: "side", header: "Side", render: (o) => <Badge tone={o.side === "BUY" ? "bull" : "bear"} variant="outline">{o.side} · executed</Badge> },
    { key: "qty", header: "Qty", align: "right", render: (o) => formatInt(o.quantity) },
    { key: "price", header: "Fill price", align: "right", render: (o) => formatPrice(o.price) },
    { key: "plan", header: "Plan", hideBelow: "sm", render: (o) => <span className="text-muted-foreground">{o.planId ?? "—"}</span> },
    { key: "at", header: "Executed", hideBelow: "md", sortValue: (o) => o.executedAt, render: (o) => <span className="text-muted-foreground">{formatDateTime(o.executedAt)}</span> },
  ];

  const exposure = holdings
    .map((h) => ({ h, risk: h.stopLoss ? Math.max(0, h.ltp - h.stopLoss) * h.quantity : null }))
    .sort((a, b) => (b.risk ?? Infinity) - (a.risk ?? Infinity));

  return (
    <PageFrame>
      <PageHeader
        title="Active trades"
        description="Open intraday positions and their risk. Every position is flattened by the 15:15 session-end exit. Values are sample data; no broker is connected."
        meta={<SampleDataBadge asOf={asOf} />}
      />

      <LifecycleStrip highlight={["order", "position"]} />

      <StatGrid label="Portfolio figures">
        <Stat
          label="Invested"
          value={formatLakhCrore(summary.invested)}
          hint={`${formatPct((summary.invested / summary.capital) * 100, { signed: false, decimals: 1 })} of ${formatLakhCrore(summary.capital)} · ${formatLakhCrore(summary.cash)} cash`}
        />
        <Stat
          label="Unrealized P&L"
          value={formatSignedInr(summary.unrealizedPnl, { decimals: false })}
          tone={summary.unrealizedPnl >= 0 ? "bull" : "bear"}
          hint={`${formatPct(pnlPct)} on invested`}
        />
        <Stat
          label="Realized P&L"
          value={formatSignedInr(summary.realizedPnl, { decimals: false })}
          tone={summary.realizedPnl >= 0 ? "bull" : "bear"}
          hint="From closed journal trades"
          href="/journal"
        />
        <Stat
          label="Open risk to stops"
          value={formatInr(summary.openRisk, { decimals: false })}
          hint={`${formatPct((summary.openRisk / summary.capital) * 100, { signed: false })} of capital`}
        />
      </StatGrid>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section aria-label="Positions and orders" className="flex min-w-0 flex-col gap-3">
          <FilterRow label="Portfolio view">
            <ChoiceGroup
              ariaLabel="Portfolio view"
              value={tab}
              onChange={setTab}
              options={[
                { value: "positions", label: "Open positions", count: positions.length },
                { value: "holdings", label: "All holdings", count: holdings.length },
                { value: "orders", label: "Executed orders", count: orders.length },
              ]}
            />
          </FilterRow>
          {tab === "orders" ? (
            <DataTable
              columns={orderCols}
              rows={orders}
              rowKey={(o) => o.id}
              caption="Executed orders"
              empty={<Empty icon={Receipt} title="No executed orders yet" description="Orders appear here once you link an executed order to a plan." />}
            />
          ) : (
            <DataTable
              columns={columns}
              rows={tab === "positions" ? positions : holdings}
              rowKey={(h) => h.symbol}
              initialSort={{ key: "pnl", dir: "desc" }}
              caption={tab === "positions" ? "Open positions" : "Holdings"}
              empty={<Empty icon={Wallet} title="No positions yet" description="Positions appear here once an order linked to a plan is executed." />}
            />
          )}
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Receipt className="size-3.5" aria-hidden /> Rows on this page represent executed trades, not proposed plans.
          </p>
        </section>

        <div className="flex min-w-0 flex-col gap-4">
          <Panel boxed title="Allocation" hint="By sector, at last close">
            <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Capital allocation by sector; values listed below">
              {slices.map((s, i) => (
                <span key={s.label} className={cn("h-full", slotFor(i))} style={{ width: `${(s.value / totalAlloc) * 100}%` }} />
              ))}
            </div>
            <ul className="flex flex-col gap-2 text-sm tabular-nums">
              {slices.map((s, i) => (
                <li key={s.label} className="flex items-center gap-2">
                  <span className={cn("size-2.5 shrink-0 rounded-full", slotFor(i))} aria-hidden />
                  <span className="min-w-0 flex-1 truncate text-muted-foreground">{s.label}</span>
                  <span className="text-foreground">{formatLakhCrore(s.value)}</span>
                  <span className="w-12 text-right text-muted-foreground">{((s.value / totalAlloc) * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel boxed title="Risk exposure" hint={`Max risk per trade: ${summary.maxRiskPerTradePct}% of capital`}>
            <ul className="flex flex-col gap-3">
              {exposure.map(({ h, risk }) => {
                const pct = risk === null ? null : (risk / summary.capital) * 100;
                const over = pct !== null && pct > summary.maxRiskPerTradePct;
                return (
                  <li key={h.symbol} className="flex flex-col gap-1">
                    <div className="flex items-center justify-between gap-2 text-sm tabular-nums">
                      <span className="font-medium text-foreground">{h.symbol}</span>
                      <span className={cn("text-xs", pct === null ? "text-warning" : over ? "text-destructive" : "text-muted-foreground")}>
                        {pct === null ? "No stop set" : `${formatInr(risk ?? 0, { decimals: false })} · ${pct.toFixed(2)}%${over ? " · over limit" : ""}`}
                      </span>
                    </div>
                    <span className="block h-1 overflow-hidden rounded-full bg-muted" aria-hidden>
                      <span
                        className={cn("block h-full rounded-full", pct === null ? "bg-warning" : over ? "bg-destructive" : "bg-chart-1")}
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
    </PageFrame>
  );
}
