import type { Metadata } from "next";
import { data } from "@/lib/data";
import { DashboardView } from "@/features/dashboard/dashboard-view";

export const metadata: Metadata = { title: "Dashboard" };

const RECENT = ["RELIANCE", "MARUTI", "HDFCBANK", "HINDUNILVR"];

export default async function DashboardPage() {
  const [indices, summary, rows, watchlists, triggers, activity] = await Promise.all([
    data.getIndices(),
    data.getDashboardSummary(),
    data.getScannerRows(),
    data.getWatchlists(),
    data.getTriggers(),
    data.getActivity(),
  ]);
  const recentAnalyses = (await Promise.all(RECENT.map((s) => data.getAnalysis(s)))).filter(
    (a): a is NonNullable<typeof a> => a !== null,
  );
  const watchlist = watchlists[0];
  const topSetups = rows
    .filter((r) => r.direction === "long" && r.signal !== "no-trade")
    .sort((a, b) => b.qualityScore - a.qualityScore)
    .slice(0, 6);

  return (
    <DashboardView
      d={{
        asOf: data.asOf,
        indices,
        summary,
        topSetups,
        watchlist,
        watchlistRows: rows.filter((r) => watchlist.symbols.includes(r.stock.symbol)),
        triggers,
        recentAnalyses,
        activity,
      }}
    />
  );
}
