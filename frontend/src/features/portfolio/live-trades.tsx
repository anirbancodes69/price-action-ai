"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Wallet } from "lucide-react";
import {
  formatDateTime,
  formatInt,
  formatPct,
  formatPrice,
  formatSignedInr,
  formatTime,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api/client";
import { fetchRiskToday } from "@/lib/api/risk";
import { fetchTradePlans } from "@/lib/api/trade-plans";
import type { TradePlan } from "@/types";
import {
  EXIT_REASONS,
  fetchPositions,
  fetchTrades,
  type LivePosition,
  type LoggedTrade,
} from "@/lib/api/trades";
import type { DataMode } from "@/lib/api/scanner";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { Badge } from "@/components/data/badge";
import { DataTable, type Column } from "@/components/data/data-table";
import { Empty } from "@/components/data/empty";
import { ErrorState } from "@/components/data/error-state";
import { LiveDataBadge } from "@/components/data/live-data-badge";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { Stat, StatGrid } from "@/components/data/stat";
import { SignalBadge } from "@/components/trading/signal-badge";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { Button } from "@/components/ui/button";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { FilterRow } from "@/components/ui/filter-row";
import { useToast } from "@/components/ui/toast";
import { RiskTodayPanel } from "@/features/dashboard/risk-today";
import type { RiskToday } from "@/types";
import { TradeDialog, type TradeDialogMode } from "./trade-dialog";

const POLL_MS = 30_000;

/**
 * Active trades over HTTP (X7, X8, X9, X11): the trades the owner logs by hand and their live P&L at the latest stored
 * 5m close. Hybrid mode only: the sample portfolio stays for mock mode.
 */
export function LiveTrades() {
  const router = useRouter();
  const toast = useToast();
  const [data, setData] = useState<{
    trades: LoggedTrade[];
    positions: LivePosition[];
    mode: DataMode;
    risk: RiskToday;
    plans: TradePlan[];
  } | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [tab, setTab] = useState<"positions" | "trades">("positions");
  const [dialog, setDialog] = useState<TradeDialogMode | null>(null);
  const warned = useRef(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [trades, live, risk, plans] = await Promise.all([
          fetchTrades(signal),
          fetchPositions(signal),
          fetchRiskToday("actual", signal),
          fetchTradePlans(signal),
        ]);
        setData({
          trades,
          positions: live.positions,
          mode: live.dataMode,
          risk,
          plans,
        });
        setError(null);
        warned.current = false;
      } catch (e) {
        if (signal?.aborted) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setError(e instanceof Error ? e : new Error("Load failed"));
        if (!warned.current) {
          warned.current = true;
          toast({
            title: "Could not refresh your trades",
            description: "Showing the last result.",
            tone: "warn",
          });
        }
      }
    },
    [router, toast],
  );

  useEffect(() => {
    const ctl = new AbortController();
    const first = window.setTimeout(() => void load(ctl.signal), 0);
    const tick = () => {
      if (document.visibilityState === "visible") void load();
    };
    const id = window.setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    return () => {
      ctl.abort();
      window.clearTimeout(first);
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [load]);

  const header = (
    <PageHeader
      title="Active trades"
      description="The trades you log from your broker, with live P&L at the latest closed 5m bar. Nothing here places an order."
      meta={
        data ? (
          data.mode === "DEMO" ? (
            <SampleDataBadge />
          ) : (
            <LiveDataBadge mode={data.mode} />
          )
        ) : undefined
      }
      actions={
        <Button variant="primary" onClick={() => setDialog({ kind: "open" })}>
          <Plus /> Log trade
        </Button>
      }
    />
  );

  if (!data) {
    return (
      <PageFrame>
        {header}
        {error ? (
          <ErrorState
            title="Your trades are not available"
            message="They could not be loaded. Nothing was changed."
            onRetry={() => void load()}
          />
        ) : (
          <TableSkeleton />
        )}
        <TradeDialog
          mode={dialog}
          onClose={() => setDialog(null)}
          onDone={() => void load()}
        />
      </PageFrame>
    );
  }

  const { trades, positions } = data;
  // A position's id is its trade's id, so two open trades in one symbol each act on their own row.
  const tradeById = new Map(trades.map((t) => [t.id, t]));
  const priced = positions.filter((p) => p.unrealisedPnl !== null);
  const unrealised = priced.reduce((s, p) => s + (p.unrealisedPnl ?? 0), 0);
  const realised = trades.reduce((s, t) => s + (t.netRealisedPnl ?? 0), 0);
  const lastPrice = positions
    .map((p) => p.priceAt)
    .filter((x): x is string => x !== null)
    .sort()
    .at(-1);

  const positionCols: Column<LivePosition>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sticky: true,
      grow: true,
      sortValue: (p) => p.symbol,
      render: (p) => (
        <Link
          href={`/analysis/${p.symbol}`}
          className="flex flex-col rounded-lg leading-tight"
        >
          <span className="text-sm font-medium text-foreground underline-offset-4 hover:underline">
            {p.symbol}
          </span>
          <span className="truncate text-xs text-muted-foreground">
            Since {formatDateTime(p.entryAt)}
          </span>
        </Link>
      ),
    },
    {
      key: "qty",
      header: "Qty",
      align: "right",
      sortValue: (p) => p.quantity,
      render: (p) => formatInt(p.quantity),
    },
    {
      key: "avg",
      header: "Avg price",
      align: "right",
      hideBelow: "md",
      sortValue: (p) => p.entryPrice,
      render: (p) => formatPrice(p.entryPrice),
    },
    {
      key: "ltp",
      header: "Last close",
      align: "right",
      sortValue: (p) => p.currentPrice ?? 0,
      render: (p) =>
        p.currentPrice === null ? (
          <span className="text-muted-foreground">No bar yet</span>
        ) : (
          <span className="flex flex-col leading-tight">
            <span className="text-foreground">
              {formatPrice(p.currentPrice)}
            </span>
            {p.priceAt && (
              <span className="text-xs text-muted-foreground">
                {formatTime(p.priceAt)} IST
              </span>
            )}
          </span>
        ),
    },
    {
      key: "pnl",
      header: "Unrealised P&L",
      align: "right",
      sortValue: (p) => p.unrealisedPnl ?? 0,
      render: (p) => {
        if (p.unrealisedPnl === null) return "—";
        const pct =
          p.currentPrice === null
            ? null
            : ((p.currentPrice - p.entryPrice) / p.entryPrice) * 100;
        return (
          <span
            className={cn(
              "flex flex-col leading-tight",
              p.unrealisedPnl >= 0 ? "text-bull" : "text-bear",
            )}
          >
            <span>{formatSignedInr(p.unrealisedPnl)}</span>
            {pct !== null && <span className="text-xs">{formatPct(pct)}</span>}
          </span>
        );
      },
    },
    {
      key: "stop",
      header: "Stop",
      align: "right",
      hideBelow: "lg",
      render: (p) =>
        p.stop === null ? (
          <span className="text-muted-foreground">Not set</span>
        ) : (
          <span className="text-bear">{formatPrice(p.stop)}</span>
        ),
    },
    {
      key: "target",
      header: "Target",
      align: "right",
      hideBelow: "xl",
      render: (p) =>
        p.target === null ? (
          <span className="text-muted-foreground">Not set</span>
        ) : (
          <span className="text-bull">{formatPrice(p.target)}</span>
        ),
    },
    {
      key: "signal",
      header: "Signal",
      hideBelow: "md",
      render: (p) =>
        p.signal === null ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          <span className="flex flex-col items-start gap-1 leading-tight">
            <SignalBadge signal={p.signal} explain={false} />
            {p.exitReason && <span className="text-xs text-muted-foreground">{EXIT_REASONS[p.exitReason] ?? p.exitReason}</span>}
          </span>
        ),
    },
    {
      key: "act",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      render: (p) => {
        const trade = tradeById.get(p.id);
        return trade ? (
          <span className="flex justify-end gap-1.5">
            <Button size="sm" variant="outline" onClick={() => setDialog({ kind: "levels", trade })}>
              Stop / target
            </Button>
            <Button size="sm" variant="outline" onClick={() => setDialog({ kind: "fill", trade, side: "SELL" })}>
              Record sell
            </Button>
          </span>
        ) : null;
      },
    },
  ];

  const tradeCols: Column<LoggedTrade>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sticky: true,
      grow: true,
      sortValue: (t) => t.symbol,
      render: (t) => (
        <span className="text-sm font-medium text-foreground">{t.symbol}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (t) => (
        <Badge
          tone={t.status === "OPEN" ? "info" : "neutral"}
          variant="outline"
        >
          {t.status === "OPEN" ? "Open" : "Closed"}
        </Badge>
      ),
    },
    {
      key: "open",
      header: "Open qty",
      align: "right",
      sortValue: (t) => t.quantityOpen,
      render: (t) => formatInt(t.quantityOpen),
    },
    {
      key: "entry",
      header: "Avg entry",
      align: "right",
      hideBelow: "md",
      render: (t) => (t.avgEntry === null ? "—" : formatPrice(t.avgEntry)),
    },
    {
      key: "exit",
      header: "Avg exit",
      align: "right",
      hideBelow: "md",
      render: (t) => (t.avgExit === null ? "—" : formatPrice(t.avgExit)),
    },
    {
      key: "net",
      header: "Net realised",
      align: "right",
      sortValue: (t) => t.netRealisedPnl ?? 0,
      render: (t) =>
        t.netRealisedPnl === null ? (
          "—"
        ) : (
          <span
            className={t.netRealisedPnl >= 0 ? "text-bull" : "text-bear"}
            title={`Gross ${formatSignedInr(t.realisedPnl ?? 0)} less charges ${formatPrice(t.charges ?? 0)}`}
          >
            {formatSignedInr(t.netRealisedPnl)}
          </span>
        ),
    },
    {
      key: "fills",
      header: "Fills",
      align: "right",
      hideBelow: "lg",
      render: (t) => t.fills.length,
    },
    {
      key: "act",
      header: <span className="sr-only">Actions</span>,
      align: "right",
      render: (t) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() =>
            setDialog({
              kind: "fill",
              trade: t,
              side: t.status === "OPEN" ? "SELL" : "BUY",
            })
          }
        >
          Record fill
        </Button>
      ),
    },
  ];

  return (
    <PageFrame>
      {header}
      <StatGrid label="Trade figures">
        <Stat
          label="Open positions"
          value={String(positions.length)}
          hint={
            lastPrice
              ? `Priced at the ${formatTime(lastPrice)} IST bar`
              : "No priced bar yet"
          }
        />
        <Stat
          label="Unrealised P&L"
          value={formatSignedInr(unrealised)}
          tone={unrealised >= 0 ? "bull" : "bear"}
          hint={
            priced.length === positions.length
              ? "Before charges"
              : `${positions.length - priced.length} position(s) without a price`
          }
        />
        <Stat
          label="Realised P&L"
          value={formatSignedInr(realised)}
          tone={realised >= 0 ? "bull" : "bear"}
          hint="Net of the charges you entered, all logged trades"
        />
      </StatGrid>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <section
          aria-label="Positions and trades"
          className="flex min-w-0 flex-col gap-3"
        >
          <FilterRow label="Trade view">
            <ChoiceGroup
              ariaLabel="Trade view"
              value={tab}
              onChange={setTab}
              options={[
                {
                  value: "positions",
                  label: "Open positions",
                  count: positions.length,
                },
                { value: "trades", label: "All trades", count: trades.length },
              ]}
            />
          </FilterRow>
          {tab === "positions" ? (
            <DataTable
              columns={positionCols}
              rows={positions}
              rowKey={(p) => p.id}
              initialSort={{ key: "pnl", dir: "desc" }}
              caption="Open positions"
              empty={
                <Empty
                  icon={Wallet}
                  title="No open positions"
                  description="Log a trade after you buy at your broker."
                />
              }
            />
          ) : (
            <DataTable
              columns={tradeCols}
              rows={trades}
              rowKey={(t) => t.id}
              caption="All trades"
              empty={
                <Empty
                  icon={Wallet}
                  title="No trades logged yet"
                  description="Use Log trade to record your first fill."
                />
              }
            />
          )}
          <p className="text-xs text-muted-foreground">
            Prices are the latest stored 5m close, shown with their bar time.
            The stop and target are the levels you entered for a trade; the
            stop counts as its open risk in today&apos;s limits.
          </p>
        </section>
        <RiskTodayPanel books={[data.risk]} />
      </div>

      <TradeDialog
        mode={dialog}
        onClose={() => setDialog(null)}
        onDone={() => void load()}
        plans={data.plans}
      />
    </PageFrame>
  );
}
