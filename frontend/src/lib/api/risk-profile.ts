/**
 * `GET/PUT /api/v1/risk-profile` (P3, P4): the owner's sizing and account limits. The ranges mirror the registry
 * (TRD-01 §6); the server validates them again and stays the authority.
 */
import { apiRequest } from "./client";

export interface RiskForm {
  capital: string;
  perTrade: string;
  maxPositionValue: string;
  dailyLoss: string;
  maxLosses: string;
  maxOpen: string;
  openRisk: string;
}

export interface ApiRiskProfile {
  version: number | null;
  trading_capital: string;
  risk_per_trade_pct: string;
  max_position_value: string;
  daily_loss_limit_pct: string;
  max_consecutive_losses: number;
  max_open_positions: number;
  max_open_risk_pct: string;
  min_rr: string | null;
  max_entry_gap_pct: string | null;
}

export interface LoadedRiskProfile {
  form: RiskForm;
  version: number | null;
  /** Overrides the form does not edit; sent back unchanged so saving does not drop them. */
  minRr: string | null;
  maxEntryGapPct: string | null;
}

const RANGES: Record<keyof RiskForm, [number, number, string]> = {
  capital: [
    10_000,
    100_000_000,
    "Capital must be between ₹10,000 and ₹10 crore",
  ],
  perTrade: [0.1, 2, "Risk per trade must be between 0.1% and 2%"],
  maxPositionValue: [
    5_000,
    1_000_000,
    "Max position value must be between ₹5,000 and ₹10 lakh",
  ],
  dailyLoss: [0.5, 5, "Daily loss limit must be between 0.5% and 5%"],
  maxLosses: [1, 10, "Max consecutive losses must be between 1 and 10"],
  maxOpen: [1, 20, "Max open positions must be between 1 and 20"],
  openRisk: [0.25, 5, "Max open risk must be between 0.25% and 5%"],
};

const INTEGER_FIELDS: (keyof RiskForm)[] = ["maxLosses", "maxOpen"];

/** Trims a decimal string: "0.5000" becomes "0.5", "100000.00" becomes "100000". */
const plain = (v: string) =>
  v.includes(".") ? v.replace(/0+$/, "").replace(/\.$/, "") : v;

export function toForm(p: ApiRiskProfile): RiskForm {
  return {
    capital: plain(p.trading_capital),
    perTrade: plain(p.risk_per_trade_pct),
    maxPositionValue: plain(p.max_position_value),
    dailyLoss: plain(p.daily_loss_limit_pct),
    maxLosses: String(p.max_consecutive_losses),
    maxOpen: String(p.max_open_positions),
    openRisk: plain(p.max_open_risk_pct),
  };
}

/** Field errors of the form, keyed by field; empty when valid. */
export function validateRisk(
  f: RiskForm,
): Partial<Record<keyof RiskForm, string>> {
  const errors: Partial<Record<keyof RiskForm, string>> = {};
  for (const key of Object.keys(RANGES) as (keyof RiskForm)[]) {
    const [min, max, message] = RANGES[key];
    const raw = f[key].trim();
    const n = Number(raw);
    const shape = INTEGER_FIELDS.includes(key) ? /^\d+$/ : /^\d+(\.\d+)?$/;
    if (!shape.test(raw) || n < min || n > max) errors[key] = message;
  }
  return errors;
}

export async function fetchRiskProfile(
  signal?: AbortSignal,
): Promise<LoadedRiskProfile> {
  const res = await apiRequest<ApiRiskProfile>("/api/v1/risk-profile", {
    signal,
  });
  return {
    form: toForm(res.data),
    version: res.data.version,
    minRr: res.data.min_rr,
    maxEntryGapPct: res.data.max_entry_gap_pct,
  };
}

export async function saveRiskProfile(
  f: RiskForm,
  keep: Pick<LoadedRiskProfile, "minRr" | "maxEntryGapPct">,
): Promise<LoadedRiskProfile> {
  const res = await apiRequest<ApiRiskProfile>("/api/v1/risk-profile", {
    method: "PUT",
    body: {
      trading_capital: f.capital.trim(),
      risk_per_trade_pct: f.perTrade.trim(),
      max_position_value: f.maxPositionValue.trim(),
      daily_loss_limit_pct: f.dailyLoss.trim(),
      max_consecutive_losses: Number(f.maxLosses),
      max_open_positions: Number(f.maxOpen),
      max_open_risk_pct: f.openRisk.trim(),
      min_rr: keep.minRr,
      max_entry_gap_pct: keep.maxEntryGapPct,
    },
  });
  return {
    form: toForm(res.data),
    version: res.data.version,
    minRr: res.data.min_rr,
    maxEntryGapPct: res.data.max_entry_gap_pct,
  };
}
