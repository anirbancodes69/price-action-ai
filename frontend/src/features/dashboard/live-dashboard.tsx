"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { ErrorState } from "@/components/data/error-state";
import { TableSkeleton } from "@/components/data/loading-skeleton";
import { ApiError } from "@/lib/api/client";
import { fetchRiskToday } from "@/lib/api/risk";
import { fetchScanner, type DataMode } from "@/lib/api/scanner";
import { fetchPositions } from "@/lib/api/trades";
import type { RiskToday, ScannerRow } from "@/types";
import { useWatchlists } from "@/features/watchlists/watchlist-store";
import { DashboardView, type DashboardData } from "./dashboard-view";

const POLL_MS = 30_000;

/** Long setups with a signal, best quality first; the same rule as the sample dashboard. */
export function topSetups(rows: ScannerRow[], n = 6): ScannerRow[] {
  return rows
    .filter((r) => r.direction === "long" && r.signal !== "no-trade")
    .sort((a, b) => b.qualityScore - a.qualityScore)
    .slice(0, n);
}

/**
 * Dashboard in HTTP mode: figures, top setups and the watchlist from the live scan, today's risk from the engine and the
 * open logged positions. Blocks with no live source yet (index series, upcoming triggers, recent analyses, activity)
 * are left out rather than shown with sample values.
 */
export function LiveDashboard() {
  const router = useRouter();
  const { watchlists } = useWatchlists();
  const [state, setState] = useState<{
    rows: ScannerRow[];
    asOf: string;
    mode: DataMode;
    risk: RiskToday;
    open: number;
  } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const [scan, risk, live] = await Promise.all([
          fetchScanner(signal),
          fetchRiskToday("actual", signal),
          fetchPositions(signal),
        ]);
        setState({
          rows: scan.rows,
          asOf: scan.meta.asOf ?? new Date().toISOString(),
          mode: scan.meta.dataMode,
          risk,
          open: live.positions.length,
        });
        setError(null);
      } catch (e) {
        if (signal?.aborted) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/login");
          return;
        }
        setError(e instanceof Error ? e : new Error("Load failed"));
      }
    },
    [router],
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

  if (!state) {
    return (
      <PageFrame>
        <PageHeader
          title="Dashboard"
          description="Today's session: setups near their trigger and your risk budget."
        />
        {error ? (
          <ErrorState
            title="The dashboard is not available"
            message="The live data could not be loaded. Nothing was changed."
            onRetry={() => void load()}
          />
        ) : (
          <TableSkeleton />
        )}
      </PageFrame>
    );
  }

  const list = watchlists[0] ?? { id: "", name: "My watchlist", symbols: [] };
  const data: DashboardData = {
    asOf: state.asOf,
    indices: [],
    summary: {
      stocksScanned: state.rows.length,
      activeSetups: state.rows.filter(
        (r) => r.direction === "long" && r.signal !== "no-trade",
      ).length,
      awaitingConfirmation: state.rows.filter(
        (r) => r.setupStatus === "awaiting-confirmation",
      ).length,
      activeTradePlans: 0,
    },
    topSetups: topSetups(state.rows),
    watchlist: list,
    watchlistRows: state.rows.filter((r) =>
      list.symbols.includes(r.stock.symbol),
    ),
    triggers: [],
    recentAnalyses: [],
    activity: [],
    riskToday: [state.risk],
    mode: state.mode,
    openPositions: state.open,
  };
  return <DashboardView d={data} />;
}
