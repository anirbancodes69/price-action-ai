/**
 * SAMPLE DATA — watchlists, trade plans, holdings, journal and activity.
 * Prices for open plans/holdings are read from the generated sample analyses
 * so numbers are consistent across screens.
 */
import type {
  ActivityItem,
  AllocationSlice,
  BacktestStrategy,
  ExecutedOrder,
  Holding,
  JournalEntry,
  PortfolioSummary,
  TradePlan,
  TriggerAlert,
  Watchlist,
} from "@/types";
import { toTick } from "./rng";
import { buildDemoAnalysis } from "./demo-analysis";

const price = (symbol: string) => buildDemoAnalysis(symbol)?.stock.price ?? 0;
const analysis = (symbol: string) => {
  const a = buildDemoAnalysis(symbol);
  if (!a) throw new Error(`Unknown sample symbol ${symbol}`);
  return a;
};

export const WATCHLISTS: Watchlist[] = [
  { id: "wl-core", name: "Swing candidates", symbols: ["RELIANCE", "ICICIBANK", "HDFCBANK", "BHARTIARTL", "LT", "SBIN", "KOTAKBANK"] },
  { id: "wl-breakouts", name: "Breakout watch", symbols: ["MARUTI", "NTPC", "TATASTEEL", "EICHERMOT", "HAL", "POLYCAB", "TVSMOTOR"] },
  { id: "wl-it", name: "IT & Tech", symbols: ["TCS", "INFY", "HCLTECH", "WIPRO", "PERSISTENT"] },
  { id: "wl-defensive", name: "Defensives", symbols: ["ITC", "HINDUNILVR", "SUNPHARMA", "DRREDDY", "POWERGRID"] },
];

/** Builds a proposed plan from a sample analysis using a fixed ₹ risk budget. */
function planFromAnalysis(
  id: string,
  symbol: string,
  status: TradePlan["status"],
  riskBudget: number,
  createdAt: string,
  extra: Partial<TradePlan> = {},
): TradePlan {
  const a = analysis(symbol);
  const { entry, stopLoss, target, riskReward } = a.levels;
  const perShare = Math.abs(entry - stopLoss);
  const quantity = Math.max(1, Math.floor(riskBudget / perShare));
  return {
    id,
    symbol,
    companyName: a.stock.name,
    setupType: a.setup.type,
    status,
    signal: a.setup.signal,
    entry,
    stopLoss,
    target,
    riskReward,
    quantity,
    riskAmount: Math.round(perShare * quantity),
    createdAt,
    updatedAt: a.asOf,
    ...extra,
  };
}

function manualPlan(p: Omit<TradePlan, "riskReward" | "riskAmount">): TradePlan {
  const risk = Math.abs(p.entry - p.stopLoss);
  return {
    ...p,
    riskReward: Math.round((Math.abs(p.target - p.entry) / risk) * 10) / 10,
    riskAmount: Math.round(risk * p.quantity),
  };
}

export function buildTradePlans(): TradePlan[] {
  return [
    planFromAnalysis("TP-1042", "RELIANCE", "pending", 5000, "2026-11-11", { note: "Waiting for close above the post-retest high." }),
    planFromAnalysis("TP-1041", "HDFCBANK", "pending", 4000, "2026-11-10"),
    planFromAnalysis("TP-1040", "INFY", "pending", 4000, "2026-11-10"),
    planFromAnalysis("TP-1039", "MARUTI", "entry-confirmed", 6000, "2026-11-07", { note: "Trigger met on 13 Nov close. No order placed yet." }),
    planFromAnalysis("TP-1038", "BEL", "pending", 3000, "2026-11-06"),
    manualPlan({ id: "TP-1031", symbol: "NTPC", companyName: "NTPC Ltd", setupType: "breakout-retest", status: "active", signal: "hold", entry: 328.4, stopLoss: 318.6, target: 356.0, quantity: 450, createdAt: "2026-10-21", updatedAt: "2026-11-13", linkedOrderId: "ORD-88213" }),
    manualPlan({ id: "TP-1029", symbol: "LT", companyName: "Larsen & Toubro Ltd", setupType: "pullback-to-support", status: "active", signal: "hold", entry: 3812.0, stopLoss: 3712.0, target: 4080.0, quantity: 40, createdAt: "2026-10-16", updatedAt: "2026-11-13", linkedOrderId: "ORD-88107" }),
    manualPlan({ id: "TP-1027", symbol: "TATASTEEL", companyName: "Tata Steel Ltd", setupType: "breakout-retest", status: "active", signal: "hold", entry: 161.2, stopLoss: 155.8, target: 176.5, quantity: 900, createdAt: "2026-10-09", updatedAt: "2026-11-13", linkedOrderId: "ORD-87940" }),
    manualPlan({ id: "TP-1024", symbol: "BHARTIARTL", companyName: "Bharti Airtel Ltd", setupType: "trend-continuation", status: "completed", signal: "exit", entry: 1948.0, stopLoss: 1896.0, target: 2075.0, quantity: 60, createdAt: "2026-09-24", updatedAt: "2026-10-30", linkedOrderId: "ORD-87511", note: "Target reached." }),
    manualPlan({ id: "TP-1021", symbol: "AXISBANK", companyName: "Axis Bank Ltd", setupType: "range-breakout", status: "completed", signal: "exit", entry: 1188.0, stopLoss: 1162.0, target: 1252.0, quantity: 120, createdAt: "2026-09-15", updatedAt: "2026-10-03", linkedOrderId: "ORD-87201", note: "Stopped out — breakout failed." }),
    manualPlan({ id: "TP-1019", symbol: "HCLTECH", companyName: "HCL Technologies Ltd", setupType: "pullback-to-support", status: "invalidated", signal: "no-trade", entry: 1642.0, stopLoss: 1598.0, target: 1745.0, quantity: 70, createdAt: "2026-09-10", updatedAt: "2026-09-19", note: "Closed below support before trigger." }),
    manualPlan({ id: "TP-1016", symbol: "TITAN", companyName: "Titan Company Ltd", setupType: "range-breakout", status: "cancelled", signal: "no-trade", entry: 3655.0, stopLoss: 3560.0, target: 3880.0, quantity: 30, createdAt: "2026-09-02", updatedAt: "2026-09-05", note: "Cancelled ahead of results." }),
  ];
}

export const EXECUTED_ORDERS: ExecutedOrder[] = [
  { id: "ORD-88213", planId: "TP-1031", symbol: "NTPC", side: "BUY", quantity: 450, price: 328.65, executedAt: "2026-10-23T09:42:00+05:30" },
  { id: "ORD-88107", planId: "TP-1029", symbol: "LT", side: "BUY", quantity: 40, price: 3814.5, executedAt: "2026-10-20T10:05:00+05:30" },
  { id: "ORD-87940", planId: "TP-1027", symbol: "TATASTEEL", side: "BUY", quantity: 900, price: 161.35, executedAt: "2026-10-13T09:58:00+05:30" },
];

export function buildHoldings(): Holding[] {
  return [
    { symbol: "NTPC", companyName: "NTPC Ltd", quantity: 450, avgPrice: 328.65, ltp: price("NTPC"), sector: "Utilities", stopLoss: 318.6, planId: "TP-1031", signal: "hold" },
    { symbol: "LT", companyName: "Larsen & Toubro Ltd", quantity: 40, avgPrice: 3814.5, ltp: price("LT"), sector: "Infrastructure", stopLoss: 3712.0, planId: "TP-1029", signal: "hold" },
    { symbol: "TATASTEEL", companyName: "Tata Steel Ltd", quantity: 900, avgPrice: 161.35, ltp: price("TATASTEEL"), sector: "Metals", stopLoss: 155.8, planId: "TP-1027", signal: "hold" },
    { symbol: "ITC", companyName: "ITC Ltd", quantity: 300, avgPrice: 398.2, ltp: price("ITC"), sector: "FMCG", signal: "hold" },
    { symbol: "SUNPHARMA", companyName: "Sun Pharmaceutical Industries Ltd", quantity: 35, avgPrice: 1754.0, ltp: price("SUNPHARMA"), sector: "Pharma", stopLoss: 1680.0, signal: "hold" },
    { symbol: "WIPRO", companyName: "Wipro Ltd", quantity: 400, avgPrice: 262.8, ltp: price("WIPRO"), sector: "IT", stopLoss: 248.0, signal: "exit" },
  ];
}

export function buildPortfolioSummary(holdings: Holding[], journal: JournalEntry[]): PortfolioSummary {
  const capital = 1_000_000;
  const invested = holdings.reduce((a, h) => a + h.avgPrice * h.quantity, 0);
  const unrealizedPnl = holdings.reduce((a, h) => a + (h.ltp - h.avgPrice) * h.quantity, 0);
  const openRisk = holdings.reduce(
    (a, h) => a + (h.stopLoss ? Math.max(0, h.ltp - h.stopLoss) * h.quantity : 0),
    0,
  );
  return {
    capital,
    invested: Math.round(invested),
    cash: Math.round(capital - invested),
    unrealizedPnl: Math.round(unrealizedPnl),
    realizedPnl: Math.round(journal.reduce((a, j) => a + j.pnl, 0)),
    openRisk: Math.round(openRisk),
    maxRiskPerTradePct: 1,
  };
}

export function buildAllocation(holdings: Holding[], cash: number): AllocationSlice[] {
  const bySector = new Map<string, number>();
  for (const h of holdings) bySector.set(h.sector, (bySector.get(h.sector) ?? 0) + h.ltp * h.quantity);
  return [...[...bySector.entries()].map(([label, value]) => ({ label, value: Math.round(value) })).sort((a, b) => b.value - a.value), { label: "Cash", value: cash }];
}

function j(e: Omit<JournalEntry, "pnl" | "rMultiple" | "outcome"> & { stop: number }): JournalEntry {
  const { stop, ...rest } = e;
  const dir = e.direction === "long" ? 1 : -1;
  const pnl = Math.round((e.exitPrice - e.entryPrice) * dir * e.quantity);
  const r = ((e.exitPrice - e.entryPrice) * dir) / Math.abs(e.entryPrice - stop);
  const rMultiple = Math.round(r * 10) / 10;
  return { ...rest, pnl, rMultiple, outcome: Math.abs(rMultiple) < 0.15 ? "breakeven" : pnl > 0 ? "win" : "loss" };
}

export const JOURNAL: JournalEntry[] = [
  j({ id: "J-221", symbol: "BHARTIARTL", setupType: "trend-continuation", direction: "long", entryDate: "2026-09-25", exitDate: "2026-10-30", entryPrice: 1949.5, exitPrice: 2074.0, stop: 1896.0, quantity: 60, followedPlan: true, notes: "Held through a shallow pullback; target filled on the gap-up.", tags: ["A+ setup", "Patient hold"] }),
  j({ id: "J-219", symbol: "AXISBANK", setupType: "range-breakout", direction: "long", entryDate: "2026-09-16", exitDate: "2026-10-03", entryPrice: 1189.0, exitPrice: 1161.5, stop: 1162.0, quantity: 120, followedPlan: true, notes: "Breakout failed back into range. Stop respected.", tags: ["Failed breakout"] }),
  j({ id: "J-216", symbol: "POWERGRID", setupType: "pullback-to-support", direction: "long", entryDate: "2026-09-08", exitDate: "2026-09-29", entryPrice: 276.4, exitPrice: 291.8, stop: 270.2, quantity: 500, followedPlan: true, notes: "Clean bounce from prior swing high.", tags: ["A+ setup"] }),
  j({ id: "J-212", symbol: "TITAN", setupType: "breakout-retest", direction: "long", entryDate: "2026-08-26", exitDate: "2026-09-01", entryPrice: 3598.0, exitPrice: 3601.0, stop: 3520.0, quantity: 30, followedPlan: false, notes: "Exited early on intraday noise — should have held per plan.", tags: ["Early exit", "Discipline"] }),
  j({ id: "J-209", symbol: "SBIN", setupType: "breakout-retest", direction: "long", entryDate: "2026-08-12", exitDate: "2026-09-04", entryPrice: 842.0, exitPrice: 902.5, stop: 818.0, quantity: 200, followedPlan: true, notes: "Textbook retest entry. Trailed stop under higher lows.", tags: ["A+ setup", "Trailing stop"] }),
  j({ id: "J-205", symbol: "DRREDDY", setupType: "pullback-to-support", direction: "long", entryDate: "2026-07-30", exitDate: "2026-08-08", entryPrice: 1298.0, exitPrice: 1262.5, stop: 1264.0, quantity: 80, followedPlan: true, notes: "Support broke on sector weakness.", tags: ["Sector headwind"] }),
  j({ id: "J-201", symbol: "EICHERMOT", setupType: "range-breakout", direction: "long", entryDate: "2026-07-14", exitDate: "2026-08-05", entryPrice: 6120.0, exitPrice: 6548.0, stop: 5960.0, quantity: 12, followedPlan: true, notes: "Volume expansion on breakout confirmed demand.", tags: ["Volume confirmation"] }),
  j({ id: "J-198", symbol: "HINDUNILVR", setupType: "range-bound", direction: "long", entryDate: "2026-07-02", exitDate: "2026-07-10", entryPrice: 2512.0, exitPrice: 2476.0, stop: 2470.0, quantity: 40, followedPlan: false, notes: "Took a mid-range entry against the rules. Avoid.", tags: ["Rule break"] }),
];

export function buildActivity(): ActivityItem[] {
  return [
    { id: "a1", kind: "trigger", title: "MARUTI — entry trigger met", detail: "Closed above the post-retest high. Plan TP-1039 moved to Entry confirmed.", at: "2026-11-13T15:31:00+05:30" },
    { id: "a2", kind: "setup", title: "RELIANCE — breakout retest detected", detail: "Retest of the prior resistance zone held on lower volume.", at: "2026-11-13T15:30:00+05:30" },
    { id: "a3", kind: "plan", title: "Trade plan TP-1042 created", detail: "RELIANCE · Breakout & Retest · proposed, not an order.", at: "2026-11-11T18:12:00+05:30" },
    { id: "a4", kind: "invalidated", title: "HCLTECH — setup invalidated", detail: "Closed below support before the trigger was met.", at: "2026-11-10T15:30:00+05:30" },
    { id: "a5", kind: "watchlist", title: "Added POLYCAB to Breakout watch", detail: "Watchlist updated.", at: "2026-11-09T11:20:00+05:30" },
    { id: "a6", kind: "journal", title: "Journal entry added for BHARTIARTL", detail: "Target reached · +2.4R.", at: "2026-10-30T19:04:00+05:30" },
  ];
}

export function buildTriggers(): TriggerAlert[] {
  const make = (id: string, symbol: string, condition: string): TriggerAlert => {
    const a = analysis(symbol);
    return {
      id,
      symbol,
      condition,
      level: a.levels.entry,
      distancePct: Math.round(((a.levels.entry - a.stock.price) / a.stock.price) * 10000) / 100,
      signal: a.setup.signal,
    };
  };
  return [
    make("t1", "RELIANCE", "Close above post-retest high"),
    make("t2", "HDFCBANK", "Close above 3-day high at support"),
    make("t3", "INFY", "Close above 3-day high at support"),
    make("t4", "BEL", "Close above 3-day high at support"),
    make("t5", "KOTAKBANK", "Close above post-retest high"),
  ];
}

export const BACKTEST_STRATEGIES: BacktestStrategy[] = [
  { id: "bo-retest", name: "Breakout & Retest", description: "Enter on confirmation after price retests a broken resistance zone." },
  { id: "pullback", name: "Pullback to Support", description: "Enter in established uptrends when price pulls back to a role-reversal level." },
  { id: "range-bo", name: "Range Breakout", description: "Enter on a closing break of a well-defined horizontal range." },
];

export const SAMPLE_EQUITY_CURVE: { time: string; value: number }[] = (() => {
  // Illustrative placeholder curve — NOT a backtest result.
  const out: { time: string; value: number }[] = [];
  let v = 100;
  const start = new Date("2025-01-06T00:00:00Z");
  for (let i = 0; i < 90; i++) {
    const d = new Date(start);
    d.setUTCDate(d.getUTCDate() + i * 7);
    v *= 1 + Math.sin(i / 6) * 0.012 + 0.003;
    out.push({ time: d.toISOString().slice(0, 10), value: toTick(v) });
  }
  return out;
})();
