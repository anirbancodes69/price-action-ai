/** Market-data domain types. These mirror the contract the backend will expose. */

export type Exchange = "NSE" | "BSE";

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
  | "Utilities";

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

export type Timeframe = "1D" | "1W" | "1M";

/** Daily bar. `time` is an ISO business day, e.g. "2026-11-13". */
export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type MarketSession = "pre-open" | "open" | "closed";
