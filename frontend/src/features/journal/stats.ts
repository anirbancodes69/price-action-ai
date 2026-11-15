import type { JournalEntry } from "@/types";

/** Descriptive statistics over journal entries (no trading rules involved). */
export function journalStats(entries: JournalEntry[]) {
  const wins = entries.filter((e) => e.outcome === "win");
  const losses = entries.filter((e) => e.outcome === "loss");
  const grossWin = wins.reduce((a, e) => a + e.pnl, 0);
  const grossLoss = Math.abs(losses.reduce((a, e) => a + e.pnl, 0));
  const net = entries.reduce((a, e) => a + e.pnl, 0);
  const avgR = entries.length ? entries.reduce((a, e) => a + e.rMultiple, 0) / entries.length : 0;
  const followed = entries.filter((e) => e.followedPlan);
  return {
    trades: entries.length,
    winRate: entries.length ? (wins.length / entries.length) * 100 : 0,
    profitFactor: grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : 0,
    net,
    avgR,
    planAdherence: entries.length ? (followed.length / entries.length) * 100 : 0,
    followedNet: followed.reduce((a, e) => a + e.pnl, 0),
    brokenNet: entries.filter((e) => !e.followedPlan).reduce((a, e) => a + e.pnl, 0),
  };
}
