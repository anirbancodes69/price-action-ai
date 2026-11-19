/**
 * Manual trade log over HTTP: `GET/POST /api/v1/actual-trades`, `POST .../{id}/fills` and `GET /api/v1/positions/live`
 * (ADR-010: the app records what the owner did at the broker; it never places an order). Decimal strings become numbers
 * here, for display only; the backend owns every figure (average cost, realised P&L, unrealised P&L).
 */
import { apiRequest, type ApiEnvelope } from "./client";
import { num, type DataMode } from "./scanner";

interface ApiFill {
  id: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: string;
  executed_at: string;
  fees: string | null;
}

export interface ApiActualTrade {
  id: string;
  instrument: { symbol: string; name: string } | null;
  trade_plan_id: string | null;
  status: "OPEN" | "CLOSED";
  stop: string | null;
  target: string | null;
  quantity_open: number;
  avg_entry_price: string | null;
  avg_exit_price: string | null;
  realized_pnl: string | null;
  charges: string | null;
  fills: ApiFill[];
}

export interface ApiPosition {
  position_id: string;
  symbol: string;
  quantity: number;
  entry_price: string;
  entry_at: string;
  current_price: string | null;
  price_at: string | null;
  unrealised_pnl: string | null;
  stop: string | null;
  target: string | null;
  signal: "HOLD" | "EXIT" | null;
  exit_reason: string | null;
}

export interface TradeFill {
  id: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  executedAt: string;
  fees: number | null;
}

export interface LoggedTrade {
  id: string;
  symbol: string;
  name: string;
  status: "OPEN" | "CLOSED";
  /** The stop and target you entered for this trade; `null` when none. */
  stop: number | null;
  target: number | null;
  quantityOpen: number;
  avgEntry: number | null;
  avgExit: number | null;
  /** Gross of charges; `null` until the first sell. */
  realisedPnl: number | null;
  charges: number | null;
  /** Realised P&L after charges; `null` until the first sell. */
  netRealisedPnl: number | null;
  fills: TradeFill[];
}

export interface LivePosition {
  id: string;
  symbol: string;
  quantity: number;
  entryPrice: number;
  entryAt: string;
  currentPrice: number | null;
  priceAt: string | null;
  unrealisedPnl: number | null;
  stop: number | null;
  target: number | null;
  /** The engine's position monitor on closed 5m bars; `null` when it could not answer. */
  signal: "hold" | "exit" | null;
  /** Why the signal is `exit`. */
  exitReason: string | null;
}

/** Plain words for the engine's exit reasons (TRD-07 §7.1). */
export const EXIT_REASONS: Record<string, string> = {
  STOP: "Stop hit",
  TARGET: "Target reached",
  STRUCTURE_EXIT: "Bearish structure break",
  SESSION_END: "Session-end exit time",
};

const opt = (v: string | null): number | null => (v === null ? null : Number(v));

export function mapTrade(t: ApiActualTrade): LoggedTrade {
  const realised = opt(t.realized_pnl);
  const charges = opt(t.charges);
  return {
    id: t.id,
    symbol: t.instrument?.symbol ?? "—",
    name: t.instrument?.name ?? "",
    status: t.status,
    stop: opt(t.stop),
    target: opt(t.target),
    quantityOpen: t.quantity_open,
    avgEntry: opt(t.avg_entry_price),
    avgExit: opt(t.avg_exit_price),
    realisedPnl: realised,
    charges,
    netRealisedPnl: realised === null ? null : realised - (charges ?? 0),
    fills: t.fills.map((f) => ({ id: f.id, side: f.side, quantity: f.quantity, price: num(f.price), executedAt: f.executed_at, fees: opt(f.fees) })),
  };
}

export function mapPosition(p: ApiPosition): LivePosition {
  return {
    id: p.position_id,
    symbol: p.symbol,
    quantity: p.quantity,
    entryPrice: num(p.entry_price),
    entryAt: p.entry_at,
    currentPrice: opt(p.current_price),
    priceAt: p.price_at,
    unrealisedPnl: opt(p.unrealised_pnl),
    stop: opt(p.stop),
    target: opt(p.target),
    signal: p.signal === "HOLD" ? "hold" : p.signal === "EXIT" ? "exit" : null,
    exitReason: p.exit_reason,
  };
}

export async function fetchTrades(signal?: AbortSignal): Promise<LoggedTrade[]> {
  const res = await apiRequest<ApiActualTrade[]>("/api/v1/actual-trades?limit=100", { signal });
  return res.data.map(mapTrade);
}

export async function fetchPositions(signal?: AbortSignal): Promise<{ positions: LivePosition[]; dataMode: DataMode }> {
  const res = await apiRequest<ApiPosition[], { data_mode?: DataMode }>("/api/v1/positions/live?book=ACTUAL", { signal });
  return { positions: res.data.map(mapPosition), dataMode: res.meta.data_mode ?? "DEMO" };
}

export interface FillForm {
  symbol: string;
  side: "BUY" | "SELL";
  quantity: string;
  price: string;
  /** `datetime-local` value (`YYYY-MM-DDTHH:mm`), read as IST. */
  executedAt: string;
  fees: string;
  /** Optional levels of a new trade. */
  stop: string;
  target: string;
}

/** Field errors of a fill form, keyed by field; empty when the form is valid. */
export function validateFill(f: FillForm, needSymbol: boolean): Partial<Record<keyof FillForm, string>> {
  const e: Partial<Record<keyof FillForm, string>> = {};
  if (needSymbol && !/^[A-Z0-9&_-]{1,32}$/.test(f.symbol.trim().toUpperCase())) e.symbol = "Enter the NSE trading symbol";
  if (!/^[1-9]\d{0,7}$/.test(f.quantity.trim())) e.quantity = "Enter a whole number of shares";
  if (!/^\d+(\.\d{1,2})?$/.test(f.price.trim()) || Number(f.price) <= 0) e.price = "Enter a price above 0 with at most two decimals";
  if (f.fees.trim() !== "" && !/^\d+(\.\d{1,2})?$/.test(f.fees.trim())) e.fees = "Enter charges as an amount, or leave empty";
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(f.executedAt)) e.executedAt = "Enter the execution time";
  if (needSymbol) {
    const price = Number(f.price);
    if (f.stop.trim() !== "" && (!/^\d+(\.\d{1,2})?$/.test(f.stop.trim()) || Number(f.stop) <= 0 || (!e.price && Number(f.stop) >= price))) e.stop = "Enter a stop below the price";
    if (f.target.trim() !== "" && (!/^\d+(\.\d{1,2})?$/.test(f.target.trim()) || Number(f.target) <= 0 || (!e.price && Number(f.target) <= price))) e.target = "Enter a target above the price";
  }
  return e;
}

/** The IST wall-clock time now, as a `datetime-local` value. */
export function nowIstLocal(now: number = Date.now()): string {
  return new Date(now + 5.5 * 3600_000).toISOString().slice(0, 16);
}

function fillBody(f: FillForm) {
  return {
    quantity: Number(f.quantity),
    price: f.price.trim(),
    executed_at: `${f.executedAt}:00+05:30`,
    ...(f.fees.trim() === "" ? {} : { fees: f.fees.trim() }),
  };
}

/** A repeated key (a double click, a retry) creates the trade or fill once. */
const key = () => ({ "Idempotency-Key": crypto.randomUUID() });

export async function logTrade(f: FillForm): Promise<LoggedTrade> {
  const res: ApiEnvelope<ApiActualTrade> = await apiRequest<ApiActualTrade>("/api/v1/actual-trades", {
    method: "POST",
    headers: key(),
    body: {
      instrument: f.symbol.trim().toUpperCase(),
      fill: { side: "BUY", ...fillBody(f) },
      ...(f.stop.trim() === "" ? {} : { stop: f.stop.trim() }),
      ...(f.target.trim() === "" ? {} : { target: f.target.trim() }),
    },
  });
  return mapTrade(res.data);
}

export async function addFill(tradeId: string, f: FillForm): Promise<LoggedTrade> {
  const res = await apiRequest<ApiActualTrade>(`/api/v1/actual-trades/${encodeURIComponent(tradeId)}/fills`, {
    method: "POST",
    headers: key(),
    body: { side: f.side, ...fillBody(f) },
  });
  return mapTrade(res.data);
}

export interface LevelsForm {
  stop: string;
  target: string;
}

/** Field errors of the stop and target form; each may be empty (cleared). */
export function validateLevels(f: LevelsForm): Partial<Record<keyof LevelsForm, string>> {
  const e: Partial<Record<keyof LevelsForm, string>> = {};
  for (const k of ["stop", "target"] as const) {
    const v = f[k].trim();
    if (v !== "" && (!/^\d+(\.\d{1,2})?$/.test(v) || Number(v) <= 0)) e[k] = "Enter a price above 0 with at most two decimals, or leave empty";
  }
  return e;
}

/** Moves or clears the stop and target of a trade; an empty field clears the level. */
export async function setLevels(tradeId: string, f: LevelsForm): Promise<LoggedTrade> {
  const res = await apiRequest<ApiActualTrade>(`/api/v1/actual-trades/${encodeURIComponent(tradeId)}`, {
    method: "PATCH",
    body: { stop: f.stop.trim() === "" ? null : f.stop.trim(), target: f.target.trim() === "" ? null : f.target.trim() },
  });
  return mapTrade(res.data);
}
