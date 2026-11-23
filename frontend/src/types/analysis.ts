import type { Candle, Stock, Timeframe } from "./market";

/** Directional bias of a market-structure read. */
export type Bias = "bullish" | "bearish" | "neutral";

export type MarketStructure =
  | "uptrend"
  | "downtrend"
  | "range"
  | "transition";

export type SetupType =
  | "opening-range-breakout"
  | "prev-day-high-break"
  | "prev-day-low-break"
  | "breakout-retest"
  | "pullback-to-support"
  | "range-breakout"
  | "breakdown-retest"
  | "trend-continuation"
  | "liquidity-sweep-reversal"
  | "failed-breakdown-reclaim"
  | "range-bound";

/**
 * Lifecycle of a detected setup. A "detected" setup is NOT an entry signal;
 * entry is only confirmed when the trigger conditions are met.
 */
export type SetupStatus =
  | "detected"
  | "awaiting-confirmation"
  | "entry-confirmed"
  | "invalidated"
  | "expired";

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

/** Session reference levels and times (TRD-03 §8, TRD-01 §4.1). OR levels are null until the opening range is complete. */
export interface SessionLevels {
  pdh: number;
  pdl: number;
  pdc: number;
  orHigh: number | null;
  orLow: number | null;
  sessionHigh: number;
  sessionLow: number;
  /** ISO timestamps (IST offset). */
  entryCutoffAt: string;
  sessionEndExitAt: string;
}

export interface StockAnalysis {
  stock: Stock;
  /** Primary analysis timeframe (5m in pa-intraday). */
  timeframe: Timeframe;
  /** End of the last completed 5m bar used (ISO timestamp, IST offset). */
  asOf: string;
  /** Completed daily bars (context and display only). */
  candles: Candle[];
  /** Completed intraday bars: 5m (primary) and 15m (context). */
  intraday: { "5m": Candle[]; "15m": Candle[] };
  session: SessionLevels;
  /** 15m structure aligned to the 5m close (TRD-02 §9). */
  htfStructure: MarketStructure;
  /** Close of the bar that produced the signal, and until when it is valid (TRD-04 §12). Null for NO TRADE. */
  signalAt: string | null;
  validUntil: string | null;

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
  /** `null` when there is no setup with levels (a NO_TRADE analysis from the live API). */
  levels: TradeLevels | null;
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
  /** `null` when there is no setup (a NO_TRADE row from the live API): no badge is shown. */
  setupStatus: SetupStatus | null;
  signal: SignalState;
  /** `null` when there is no setup with levels (a NO_TRADE row from the live API). */
  levels: TradeLevels | null;
  qualityScore: number;
  htfStructure: MarketStructure;
  signalAt: string | null;
  validUntil: string | null;
}
