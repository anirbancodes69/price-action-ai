/**
 * `GET /api/v1/scanner` (N1) and its mapping to the frontend `ScannerRow` (ADR-016, TRD-04 §13).
 * The canonical engine vocabulary is mapped here, at the adapter boundary, never in components. Only formatting
 * conversions happen (decimal strings to numbers for display); no trading values are computed.
 */
import type { MarketStructure, ScannerRow, SetupStatus, SetupType, SignalState } from "@/types";
import { apiRequest } from "./client";

export type ApiStructure = "BULLISH" | "BEARISH" | "SIDEWAYS" | "TRANSITION";

export interface ApiScannerRow {
  instrument: { symbol: string; name: string; exchange: string; sector: string | null };
  last_close: string;
  change: string | null;
  change_pct: string | null;
  as_of: string;
  htf_state: ApiStructure | null;
  structure_state: ApiStructure | null;
  signal_state: string;
  signal_at: string | null;
  valid_until: string | null;
  primary_setup: {
    type: string;
    direction: "LONG" | "SHORT";
    status: string;
    levels: { trigger: string; entry: string; stop: string; target: string; rr: string; target_source: string } | null;
    quality_score: number;
  } | null;
}

export type DataMode = "DEMO" | "PERSONAL" | "LICENSED";

export interface ScannerMeta {
  dataMode: DataMode;
  asOf: string | null;
  nextBarClose: string | null;
  total: number;
  notice: string | null;
}

const STRUCTURE: Record<ApiStructure, MarketStructure> = {
  BULLISH: "uptrend",
  BEARISH: "downtrend",
  SIDEWAYS: "range",
  TRANSITION: "transition",
};

export const SETUP_TYPE: Record<string, SetupType> = {
  OPENING_RANGE_BREAKOUT: "opening-range-breakout",
  PREV_DAY_HIGH_BREAK: "prev-day-high-break",
  PREV_DAY_LOW_BREAK: "prev-day-low-break",
  BREAKOUT_RETEST: "breakout-retest",
  TREND_CONTINUATION: "trend-continuation",
  LIQUIDITY_SWEEP_REVERSAL: "liquidity-sweep-reversal",
  FAILED_BREAKDOWN_RECLAIM: "failed-breakdown-reclaim",
};

export const SETUP_STATUS: Record<string, SetupStatus> = {
  FORMING: "detected",
  AWAITING_CONFIRMATION: "awaiting-confirmation",
  ENTRY_CONFIRMED: "entry-confirmed",
  INVALIDATED: "invalidated",
  EXPIRED: "expired",
};

export const SIGNAL: Record<string, SignalState> = {
  BUY_WATCH: "buy-watch",
  ENTRY_CONFIRMED: "entry-confirmed",
  HOLD: "hold",
  EXIT: "exit",
  NO_TRADE: "no-trade",
};

export const num = (v: string | null | undefined): number => (v == null ? 0 : Number(v));

export function mapStructure(s: ApiStructure | null): MarketStructure {
  return s ? STRUCTURE[s] : "range";
}

export function mapScannerRow(r: ApiScannerRow): ScannerRow {
  const p = r.primary_setup;
  const long = (p?.direction ?? "LONG") === "LONG";
  const structure = mapStructure(r.structure_state);
  const levels = p?.levels
    ? { entry: num(p.levels.entry), stopLoss: num(p.levels.stop), target: num(p.levels.target), riskReward: num(p.levels.rr) }
    : null;
  return {
    stock: {
      symbol: r.instrument.symbol,
      name: r.instrument.name,
      exchange: "NSE",
      sector: "Unclassified",
      indices: ["NIFTY 50"],
      price: num(r.last_close),
      change: num(r.change),
      changePct: num(r.change_pct),
      volume: 0, // not supplied by the live API
    },
    structure,
    bias: structure === "uptrend" ? "bullish" : structure === "downtrend" ? "bearish" : "neutral",
    // No primary setup is a valid result (NO_TRADE), shown as range-bound / no edge (TRD-04 §13).
    setupType: p ? (SETUP_TYPE[p.type] ?? "range-bound") : "range-bound",
    direction: long ? "long" : "short",
    setupStatus: p ? (SETUP_STATUS[p.status] ?? "detected") : null,
    signal: SIGNAL[r.signal_state] ?? "no-trade",
    levels,
    qualityScore: p?.quality_score ?? 0,
    htfStructure: mapStructure(r.htf_state),
    signalAt: r.signal_at,
    validUntil: r.valid_until,
  };
}

export async function fetchScanner(signal?: AbortSignal): Promise<{ rows: ScannerRow[]; meta: ScannerMeta }> {
  const res = await apiRequest<ApiScannerRow[], { data_mode?: DataMode; as_of?: string | null; next_bar_close?: string | null; total?: number; notice?: string | null }>(
    "/api/v1/scanner?limit=100",
    { signal },
  );
  return {
    rows: res.data.map(mapScannerRow),
    meta: {
      dataMode: res.meta.data_mode ?? "DEMO",
      asOf: res.meta.as_of ?? null,
      nextBarClose: res.meta.next_bar_close ?? null,
      total: res.meta.total ?? res.data.length,
      notice: res.meta.notice ?? null,
    },
  };
}
