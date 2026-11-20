/**
 * `GET /api/v1/analysis/{symbol}?include=candles,candles_15m,candles_1d` (N5) and its mapping to the frontend `StockAnalysis` (ADR-016).
 * Like the scanner, the canonical vocabulary is mapped at this boundary and only formatting conversions happen
 * (decimal strings to numbers). Nothing is calculated here: entry, stop, target, score and signal come from the engine.
 */
import type { Bias, Candle, EvidenceItem, PriceZone, QualityFactor, StockAnalysis, StructureBreak, SwingPoint } from "@/types";
import { SIGNAL_REASONS } from "../labels";
import { apiRequest } from "./client";
import { SETUP_STATUS, SETUP_TYPE, SIGNAL, mapStructure, num, type ApiStructure, type DataMode } from "./scanner";

interface ApiSessionLevels {
  pdh: string | null;
  pdl: string | null;
  pdc: string | null;
  or_high: string | null;
  or_low: string | null;
  session_high: string;
  session_low: string;
  entry_cutoff_at: string;
  session_end_exit_at: string;
}

interface ApiSetup {
  id: string;
  type: string;
  direction: "LONG" | "SHORT";
  informational: boolean;
  status: string;
  levels: { trigger: string; entry: string; stop: string; target: string; rr: string; target_source: string } | null;
  quality: { score: number; version: string; components: { key: string; label: string; points: number; max: number; missing: boolean }[] };
}

export interface ApiAnalysisRun {
  id: string;
  instrument: { symbol: string; name: string; exchange: string };
  as_of: string;
  status: "COMPLETED" | "INSUFFICIENT_HISTORY" | "INVALID_INPUT" | "FAILED";
  context: { htf_state: ApiStructure | null; session: ApiSessionLevels | null };
  structure: { state: ApiStructure; transition_direction: "UP" | "DOWN" | null };
  signal: { state: string; reason_codes: string[]; signal_at: string | null; valid_until: string | null };
  primary_setup_id: string | null;
  setups: ApiSetup[];
  swings: { kind: "HIGH" | "LOW"; bar_start: string; price: string; label: string }[];
  events: { type: string; direction: "UP" | "DOWN"; level: string; level_bar_start: string; break_bar_start: string }[];
  zones: { id: string; role: "SUPPORT" | "RESISTANCE"; low: string; high: string; touches: number; strength_bucket: string; formed_at: string }[];
  candles?: ApiCandle[];
  candles_15m?: ApiCandle[];
  candles_1d?: ApiCandle[];
}

interface ApiCandle {
  start: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
}

export interface AnalysisMeta {
  dataMode: DataMode;
  nextBarClose: string | null;
}

const BIAS: Record<ApiStructure, Bias> = { BULLISH: "bullish", BEARISH: "bearish", SIDEWAYS: "neutral", TRANSITION: "neutral" };
const SWING_LABELS = new Set(["HH", "HL", "LH", "LL"]);

/** Why the run cannot be drawn (no session levels or not enough history), or null when it can. */
export function analysisProblem(run: ApiAnalysisRun): string | null {
  if (run.status === "INSUFFICIENT_HISTORY") return "Not enough stored bars for this symbol yet.";
  if (run.status !== "COMPLETED" || !run.context.session) return "The analysis is not available for this bar.";
  return null;
}

export function mapAnalysis(run: ApiAnalysisRun): StockAnalysis {
  const s = run.context.session;
  if (!s) throw new Error("Analysis has no session levels");
  const toCandles = (bars: ApiCandle[] | undefined, daily = false): Candle[] =>
    (bars ?? []).map((c) => ({
      time: daily ? c.start.slice(0, 10) : c.start, // daily bars are keyed by session date
      open: num(c.open),
      high: num(c.high),
      low: num(c.low),
      close: num(c.close),
      volume: c.volume,
    }));
  const candles = toCandles(run.candles);
  const price = candles.length ? candles[candles.length - 1].close : 0;
  const pdc = num(s.pdc);
  const primary = run.setups.find((x) => x.id === run.primary_setup_id) ?? null;
  const signal = SIGNAL[run.signal.state] ?? "no-trade";

  const swings: SwingPoint[] = run.swings
    .filter((p) => SWING_LABELS.has(p.label))
    .map((p) => ({ time: p.bar_start, price: num(p.price), kind: p.kind === "HIGH" ? "high" : "low", label: p.label as SwingPoint["label"] }));
  const breaks: StructureBreak[] = run.events
    .filter((e) => e.type === "BOS" || e.type === "CHOCH")
    .map((e) => ({
      kind: e.type === "BOS" ? "BOS" : "CHoCH",
      direction: e.direction === "UP" ? "bullish" : "bearish",
      level: num(e.level),
      fromTime: e.level_bar_start,
      toTime: e.break_bar_start,
    }));
  const zones: PriceZone[] = run.zones.map((z) => ({
    id: z.id,
    kind: z.role === "SUPPORT" ? "support" : "resistance",
    low: num(z.low),
    high: num(z.high),
    label: z.role === "SUPPORT" ? "Support" : "Resistance",
    touches: z.touches,
    fromTime: z.formed_at,
    strength: z.strength_bucket === "STRONG" ? "strong" : z.strength_bucket === "MODERATE" ? "moderate" : "weak",
  }));
  const factors: QualityFactor[] = (primary?.quality.components ?? []).map((c) => ({
    label: c.label,
    score: c.max > 0 ? Math.round((c.points / c.max) * 100) : 0,
    note: c.missing ? "Not available" : `${c.points} of ${c.max} points`,
  }));
  const lv = primary?.levels;
  // Evidence restates engine output only: each PAQS component (supporting when it scored, caution when it
  // scored nothing or was missing) and the engine's own reason codes. No threshold is applied here.
  const evidence: EvidenceItem[] = [
    ...(primary?.quality.components ?? []).map((c): EvidenceItem => {
      const scored = !c.missing && c.points > 0;
      return {
        title: c.label,
        detail: c.missing ? "Not available for this bar." : `${c.points} of ${c.max} points.`,
        tone: scored ? "supporting" : "caution",
      };
    }),
    ...run.signal.reason_codes.map((code): EvidenceItem => ({ title: SIGNAL_REASONS[code] ?? code, detail: "Reported by the engine.", tone: "caution" })),
  ];

  return {
    stock: {
      symbol: run.instrument.symbol,
      name: run.instrument.name,
      exchange: "NSE",
      sector: "Unclassified",
      indices: ["NIFTY 50"],
      price,
      change: pdc > 0 ? price - pdc : 0,
      changePct: pdc > 0 ? ((price - pdc) / pdc) * 100 : 0,
      volume: candles.reduce((v, c) => v + c.volume, 0),
    },
    timeframe: "5m",
    asOf: run.as_of,
    candles: toCandles(run.candles_1d, true),
    intraday: { "5m": candles, "15m": toCandles(run.candles_15m) },
    session: {
      pdh: num(s.pdh),
      pdl: num(s.pdl),
      pdc,
      orHigh: s.or_high === null ? null : num(s.or_high),
      orLow: s.or_low === null ? null : num(s.or_low),
      sessionHigh: num(s.session_high),
      sessionLow: num(s.session_low),
      entryCutoffAt: s.entry_cutoff_at,
      sessionEndExitAt: s.session_end_exit_at,
    },
    htfStructure: mapStructure(run.context.htf_state),
    signalAt: run.signal.signal_at,
    validUntil: run.signal.valid_until,
    structure: mapStructure(run.structure.state),
    bias: BIAS[run.structure.state],
    trendSummary: `5m structure is ${run.structure.state.toLowerCase()}; 15m structure is ${(run.context.htf_state ?? "unknown").toLowerCase()}.`,
    swings,
    breaks,
    zones,
    events: [],
    setup: {
      type: primary ? (SETUP_TYPE[primary.type] ?? "range-bound") : "range-bound",
      direction: (primary?.direction ?? "LONG") === "LONG" ? "long" : "short",
      status: primary ? (SETUP_STATUS[primary.status] ?? "detected") : "detected",
      signal,
      headline: primary
        ? `Engine signal: ${run.signal.state.replaceAll("_", " ").toLowerCase()}.`
        : "No setup on the latest closed bar. No-trade is a valid outcome.",
    },
    levels: lv ? { entry: num(lv.entry), stopLoss: num(lv.stop), target: num(lv.target), riskReward: num(lv.rr) } : null,
    qualityScore: primary?.quality.score ?? 0,
    qualityFactors: factors,
    entryConditions: lv ? [`Trigger above ${lv.trigger}, entry at the next 5m open.`] : [],
    invalidation: lv ? [`A close below the stop at ${lv.stop}.`] : [],
    evidence,
  };
}

export async function fetchAnalysis(symbol: string, signal?: AbortSignal): Promise<{ run: ApiAnalysisRun; meta: AnalysisMeta }> {
  const res = await apiRequest<ApiAnalysisRun, { data_mode?: DataMode; next_bar_close?: string | null }>(
    `/api/v1/analysis/${encodeURIComponent(symbol)}?include=candles,candles_15m,candles_1d`,
    { signal },
  );
  return { run: res.data, meta: { dataMode: res.meta.data_mode ?? "DEMO", nextBarClose: res.meta.next_bar_close ?? null } };
}
