/**
 * `GET /api/v1/risk/today` (R2): the account state of one book for the session. The engine applies the limits; this
 * only renames the engine's block codes and converts decimal strings for display.
 */
import type { AccountBlockReason, Book, RiskToday } from "@/types";
import { apiRequest } from "./client";
import { num } from "./scanner";

export interface ApiRiskToday {
  book: "PAPER" | "ACTUAL";
  session_date: string;
  realised_net_pnl_today: string;
  open_risk: string;
  losing_streak: number;
  open_positions: number;
  daily_loss_limit: string;
  remaining_daily_loss: string;
  max_consecutive_losses: number;
  max_open_positions: number;
  blocked_reason: string | null;
}

const BLOCK: Record<string, AccountBlockReason> = {
  DAILY_LOSS_LIMIT_REACHED: "daily-loss-limit",
  MAX_CONSECUTIVE_LOSSES_REACHED: "max-consecutive-losses",
  MAX_POSITIONS_REACHED: "max-open-positions",
  OPEN_RISK_LIMIT_REACHED: "open-risk-limit",
  ENTRY_CUTOFF_PASSED: "entry-cutoff-passed",
  SESSION_CLOSED: "session-closed",
};

export function mapRiskToday(r: ApiRiskToday): RiskToday {
  return {
    book: r.book === "PAPER" ? "paper" : "actual",
    sessionDate: r.session_date,
    realisedNetPnl: num(r.realised_net_pnl_today),
    openRisk: num(r.open_risk),
    losingStreak: r.losing_streak,
    openPositions: r.open_positions,
    dailyLossLimit: num(r.daily_loss_limit),
    remainingDailyLoss: num(r.remaining_daily_loss),
    maxConsecutiveLosses: r.max_consecutive_losses,
    maxOpenPositions: r.max_open_positions,
    blockedReason:
      r.blocked_reason === null ? null : (BLOCK[r.blocked_reason] ?? null),
  };
}

export async function fetchRiskToday(
  book: Book,
  signal?: AbortSignal,
): Promise<RiskToday> {
  const res = await apiRequest<ApiRiskToday>(
    `/api/v1/risk/today?book=${book === "paper" ? "PAPER" : "ACTUAL"}`,
    { signal },
  );
  return mapRiskToday(res.data);
}
