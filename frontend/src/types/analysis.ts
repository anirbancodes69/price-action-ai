import type { Candle, Stock, Timeframe } from "./market";

/** Directional bias of a market-structure read. */
export type Bias = "bullish" | "bearish" | "neutral";

export type MarketStructure =
  | "uptrend"
  | "downtrend"
  | "range"
  | "transition";

export type SetupType =
  | "breakout-retest"
  | "pullback-to-support"
  | "range-breakout"
  | "breakdown-retest"
  | "trend-continuation"
  | "range-bound";

/**
 * Lifecycle of a detected setup. A "detected" setup is NOT an entry signal;
 * entry is only confirmed when the trigger conditions are met.
 */
export type SetupStatus =
  | "detected"
  | "awaiting-confirmation"
  | "entry-confirmed"
  | "invalidated";

/**
 * Action state shown to the trader. Never a bare BUY/SELL — each state is
 * accompanied by its explanation in the UI.
 */
export type SignalState =
  | "buy-watch"
  | "entry-confirmed"
  | "hold"
  | "exit"
  | "no-trade";

export type SwingLabel = "HH" | "HL" | "LH" | "LL";

export interface SwingPoint {
  time: string;
  price: number;
  kind: "high" | "low";
  label: SwingLabel;
}

export interface StructureBreak {
  kind: "BOS" | "CHoCH";
  direction: Bias;
  /** Price level that was broken. */
  level: number;
  /** Swing that defined the level. */
  fromTime: string;
  /** Bar that closed beyond the level. */
  toTime: string;
}

export interface PriceZone {
  id: string;
  kind: "support" | "resistance";
  low: number;
  high: number;
  label: string;
  touches: number;
  /** Zone is drawn from this bar to the right edge. */
  fromTime: string;
  strength: "weak" | "moderate" | "strong";
}

export interface ChartEvent {
  kind: "breakout" | "retest" | "breakdown";
  time: string;
  price: number;
  label: string;
}

export interface TradeLevels {
  entry: number;
  stopLoss: number;
  target: number;
  /** Reward ÷ risk, e.g. 2.4 means 1 : 2.4 */
  riskReward: number;
}

export interface QualityFactor {
  label: string;
  score: number; // 0–100
  note: string;
}

export interface EvidenceItem {
  title: string;
  detail: string;
  tone: "supporting" | "caution";
}

export interface StockAnalysis {
  stock: Stock;
  timeframe: Timeframe;
  asOf: string;
  candles: Candle[];

  structure: MarketStructure;
  bias: Bias;
  trendSummary: string;

  swings: SwingPoint[];
  breaks: StructureBreak[];
  zones: PriceZone[];
  events: ChartEvent[];

  setup: {
    type: SetupType;
    /** Long setups are actionable for cash-equity swing traders; short-side levels are reference only. */
    direction: "long" | "short";
    status: SetupStatus;
    signal: SignalState;
    headline: string;
  };
  levels: TradeLevels;
  qualityScore: number; // 0–100
  qualityFactors: QualityFactor[];
  entryConditions: string[];
  invalidation: string[];
  evidence: EvidenceItem[];
}

/** Lightweight row used by the scanner and dashboards. */
export interface ScannerRow {
  stock: Stock;
  structure: MarketStructure;
  bias: Bias;
  setupType: SetupType;
  direction: "long" | "short";
  setupStatus: SetupStatus;
  signal: SignalState;
  levels: TradeLevels;
  qualityScore: number;
}
