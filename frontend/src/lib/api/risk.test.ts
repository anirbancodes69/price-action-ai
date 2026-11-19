import { describe, expect, it } from "vitest";
import { mapRiskToday, type ApiRiskToday } from "./risk";

const base: ApiRiskToday = {
  book: "ACTUAL",
  session_date: "2026-11-18",
  realised_net_pnl_today: "-59.00",
  open_risk: "250.00",
  losing_streak: 1,
  open_positions: 1,
  daily_loss_limit: "1500.00",
  remaining_daily_loss: "1191.00",
  max_consecutive_losses: 3,
  max_open_positions: 2,
  blocked_reason: null,
};

describe("mapRiskToday", () => {
  it("converts decimals and keeps the engine's figures as given", () => {
    expect(mapRiskToday(base)).toEqual({
      book: "actual",
      sessionDate: "2026-11-18",
      realisedNetPnl: -59,
      openRisk: 250,
      losingStreak: 1,
      openPositions: 1,
      dailyLossLimit: 1500,
      remainingDailyLoss: 1191,
      maxConsecutiveLosses: 3,
      maxOpenPositions: 2,
      blockedReason: null,
    });
  });

  it("renames each block code", () => {
    const code = (c: string) =>
      mapRiskToday({ ...base, blocked_reason: c }).blockedReason;
    expect(code("DAILY_LOSS_LIMIT_REACHED")).toBe("daily-loss-limit");
    expect(code("MAX_CONSECUTIVE_LOSSES_REACHED")).toBe(
      "max-consecutive-losses",
    );
    expect(code("MAX_POSITIONS_REACHED")).toBe("max-open-positions");
    expect(code("ENTRY_CUTOFF_PASSED")).toBe("entry-cutoff-passed");
    expect(code("SESSION_CLOSED")).toBe("session-closed");
  });
});
