/**
 * Trade plans over HTTP (T1, T2, T5; ADR-017). The engine sizes every plan: the client sends levels and, at most, a risk
 * percentage, never a quantity. Statuses and setup types are renamed here, at the adapter boundary.
 */
import type { SetupType, TradePlan, TradePlanStatus } from "@/types";
import { apiRequest } from "./client";
import { SETUP_TYPE, num } from "./scanner";

export interface ApiTradePlan {
  id: string;
  plan_number: string;
  instrument: { symbol: string; name: string } | null;
  status: string;
  status_reason: string | null;
  entry: string;
  stop: string;
  target: string;
  quantity: number;
  risk_amount: string;
  rr: string;
  note: string | null;
  setup_type: string | null;
  created_at: string;
  updated_at: string;
  linked: { actual_trade_ids: string[] };
}

const STATUS: Record<string, TradePlanStatus> = {
  PENDING: "pending",
  TRIGGERED: "entry-confirmed",
  FILLED: "active",
  SKIPPED: "invalidated",
  INVALIDATED: "invalidated",
  EXPIRED: "invalidated",
  CANCELLED: "cancelled",
};

/** The API's setup type for a frontend one (the reverse of the scanner mapping). */
export function apiSetupType(t: SetupType): string | null {
  return Object.entries(SETUP_TYPE).find(([, v]) => v === t)?.[0] ?? null;
}

export function mapTradePlan(p: ApiTradePlan): TradePlan {
  const status = STATUS[p.status] ?? "pending";
  return {
    id: p.plan_number,
    apiId: p.id,
    symbol: p.instrument?.symbol ?? "—",
    companyName: p.instrument?.name ?? "",
    setupType: p.setup_type ? (SETUP_TYPE[p.setup_type] ?? null) : null,
    status,
    signal: status === "pending" ? "buy-watch" : status === "entry-confirmed" ? "entry-confirmed" : "no-trade",
    entry: num(p.entry),
    stopLoss: num(p.stop),
    target: num(p.target),
    riskReward: num(p.rr),
    quantity: p.quantity,
    riskAmount: num(p.risk_amount),
    createdAt: p.created_at,
    updatedAt: p.updated_at,
    note: p.note ?? undefined,
    linkedOrderId: p.linked.actual_trade_ids[0],
  };
}

export async function fetchTradePlans(signal?: AbortSignal): Promise<TradePlan[]> {
  const res = await apiRequest<ApiTradePlan[]>("/api/v1/trade-plans?limit=100", { signal });
  return res.data.map(mapTradePlan);
}

export async function cancelTradePlan(apiId: string): Promise<void> {
  await apiRequest(`/api/v1/trade-plans/${encodeURIComponent(apiId)}/cancel`, { method: "POST", body: {} });
}

export interface PlanLevelsForm {
  entry: string;
  stop: string;
  target: string;
}

/** Field errors of the plan levels form (long plans: stop below entry, target above). */
export function validatePlanLevels(f: PlanLevelsForm): Partial<Record<keyof PlanLevelsForm, string>> {
  const e: Partial<Record<keyof PlanLevelsForm, string>> = {};
  const price = /^\d{1,9}(\.\d{1,2})?$/;
  for (const k of ["entry", "stop", "target"] as const) {
    if (!price.test(f[k].trim()) || Number(f[k]) <= 0) e[k] = "Enter a price with at most two decimals";
  }
  const [en, st, ta] = [Number(f.entry), Number(f.stop), Number(f.target)];
  if (!e.entry && !e.stop && st >= en) e.stop = "Stop-loss must be below entry for a long plan";
  if (!e.entry && !e.target && ta <= en) e.target = "Target must be above entry";
  return e;
}

/** Creates a plan from the live setup of `setupType` with the given levels; the engine sizes it. */
export async function createTradePlan(symbol: string, setupType: SetupType, f: PlanLevelsForm, riskPct?: string): Promise<TradePlan> {
  const api = apiSetupType(setupType);
  const res = await apiRequest<ApiTradePlan>("/api/v1/trade-plans", {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID() },
    body: {
      instrument: symbol,
      ...(api ? { setup_type: api } : {}),
      entry: f.entry.trim(),
      stop: f.stop.trim(),
      target: f.target.trim(),
      ...(riskPct && riskPct.trim() !== "" ? { risk_per_trade_pct: riskPct.trim() } : {}),
    },
  });
  return mapTradePlan(res.data);
}
