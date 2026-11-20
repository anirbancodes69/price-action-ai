/** Market-data domain types. These mirror the contract the backend will expose. */

/** NSE only (ADR-014); the API carries the exchange per instrument. */
export type Exchange = "NSE";

export type IndexMembership = "NIFTY 50" | "NIFTY NEXT 50" | "NIFTY MIDCAP 100";

export type Sector =
  | "Energy"
  | "IT"
  | "Banking"
  | "Financial Services"
  | "FMCG"
  | "Automobile"
  | "Pharma"
  | "Metals"
  | "Infrastructure"
  | "Consumer"
  | "Telecom"
  | "Capital Goods"
  | "Cement"
  | "Utilities"
  /** Live data without a sector classification. */
  | "Unclassified";

export interface Stock {
  symbol: string;
  name: string;
  exchange: Exchange;
  sector: Sector;
  indices: IndexMembership[];
  /** Last available close (sample data). */
  price: number;
  change: number;
  changePct: number;
  volume: number;
}

export interface MarketIndex {
  id: string;
  name: string;
  value: number;
  change: number;
  changePct: number;
  /** Small series for sparklines; oldest → newest. */
  trend: number[];
}

/**
 * Chart/analysis timeframe (ADR-014): 5m is primary, 15m is context, 1D is context and display only.
 * 1m is reserved and not used yet.
 */
export type Timeframe = "5m" | "15m" | "1D";

/**
 * One completed bar. `time` is the bar start: an ISO-8601 timestamp with the IST offset for intraday bars
 * (e.g. "2026-11-13T10:35:00+05:30") or the session date for daily bars (e.g. "2026-11-13") (ARC-04 §2.9).
 */
export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}
