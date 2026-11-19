import { describe, expect, it } from "vitest";
import {
  toForm,
  validateRisk,
  type ApiRiskProfile,
  type RiskForm,
} from "./risk-profile";

const api: ApiRiskProfile = {
  version: 2,
  trading_capital: "250000.00",
  risk_per_trade_pct: "0.75",
  max_position_value: "80000.00",
  daily_loss_limit_pct: "2",
  max_consecutive_losses: 4,
  max_open_positions: 3,
  max_open_risk_pct: "1.5",
  min_rr: null,
  max_entry_gap_pct: null,
};

const form: RiskForm = {
  capital: "250000",
  perTrade: "0.75",
  maxPositionValue: "80000",
  dailyLoss: "2",
  maxLosses: "4",
  maxOpen: "3",
  openRisk: "1.5",
};

describe("toForm", () => {
  it("shows plain numbers without trailing zeros", () => {
    expect(toForm(api)).toEqual(form);
    expect(
      toForm({
        ...api,
        risk_per_trade_pct: "0.5000",
        trading_capital: "100000.00",
      }).perTrade,
    ).toBe("0.5");
  });
});

describe("validateRisk", () => {
  it("accepts the registry defaults and the owner's values", () => {
    expect(validateRisk(form)).toEqual({});
    expect(
      validateRisk({
        capital: "100000",
        perTrade: "0.5",
        maxPositionValue: "50000",
        dailyLoss: "1.5",
        maxLosses: "3",
        maxOpen: "2",
        openRisk: "1.0",
      }),
    ).toEqual({});
  });

  it("flags values outside the ranges and malformed numbers", () => {
    const e = validateRisk({
      capital: "5000",
      perTrade: "2.5",
      maxPositionValue: "abc",
      dailyLoss: "6",
      maxLosses: "1.5",
      maxOpen: "0",
      openRisk: "0.1",
    });
    expect(Object.keys(e).sort()).toEqual([
      "capital",
      "dailyLoss",
      "maxLosses",
      "maxOpen",
      "maxPositionValue",
      "openRisk",
      "perTrade",
    ]);
  });

  it("keeps the range edges valid", () => {
    expect(
      validateRisk({
        ...form,
        perTrade: "0.1",
        dailyLoss: "5",
        maxLosses: "10",
        maxOpen: "20",
        openRisk: "0.25",
      }),
    ).toEqual({});
  });
});
