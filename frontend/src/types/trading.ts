import type { SetupType, SignalState } from "./analysis";

/**
 * A trade plan is a PROPOSAL the trader writes against a setup. It is not an
 * order. Orders and positions are separate types below.
 */
export type TradePlanStatus =
  | "pending"
  | "entry-confirmed"
  | "active"
  | "completed"
  | "invalidated"
  | "cancelled";

export interface TradePlan {
  id: string;
  symbol: string;
  companyName: string;
  setupType: SetupType;
  status: TradePlanStatus;
  signal: SignalState;
  entry: number;
  stopLoss: number;
  target: number;
  riskReward: number;
  quantity: number;
  /** Capital at risk if the stop is hit: (entry − stop) × qty. */
  riskAmount: number;
  createdAt: string;
  updatedAt: string;
  note?: string;
  /** Set when an actual order was linked to this plan. */
  linkedOrderId?: string;
}

/** An ACTUAL executed order (broker-confirmed in future phases). */
export interface ExecutedOrder {
  id: string;
  planId?: string;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  executedAt: string;
}

export interface Holding {
  symbol: string;
  companyName: string;
  quantity: number;
  avgPrice: number;
  ltp: number;
  sector: string;
  /** Stop currently protecting the position, if any. */
  stopLoss?: number;
  planId?: string;
  signal: SignalState;
}

export interface PortfolioSummary {
  capital: number;
  invested: number;
  cash: number;
  unrealizedPnl: number;
  realizedPnl: number;
  /** Sum of open risk to stops, absolute ₹. */
  openRisk: number;
  maxRiskPerTradePct: number;
}

export interface AllocationSlice {
  label: string;
  value: number;
}

export type TradeOutcome = "win" | "loss" | "breakeven";

export interface JournalEntry {
  id: string;
  symbol: string;
  setupType: SetupType;
  direction: "long" | "short";
  entryDate: string;
  exitDate: string;
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  rMultiple: number;
  outcome: TradeOutcome;
  followedPlan: boolean;
  notes: string;
  tags: string[];
}

export interface ActivityItem {
  id: string;
  kind: "setup" | "plan" | "trigger" | "invalidated" | "journal" | "watchlist";
  title: string;
  detail: string;
  at: string;
}

export interface TriggerAlert {
  id: string;
  symbol: string;
  condition: string;
  level: number;
  distancePct: number;
  signal: SignalState;
}

export interface Watchlist {
  id: string;
  name: string;
  symbols: string[];
}

export interface BacktestStrategy {
  id: string;
  name: string;
  description: string;
}
