import { describe, expect, it } from "vitest";
import { apiSetupType, mapTradePlan, validatePlanLevels, type ApiTradePlan } from "./trade-plans";

const api: ApiTradePlan = {
  id: "uuid-1",
  plan_number: "TP-0001",
  instrument: { symbol: "RELIANCE", name: "Reliance Industries" },
  status: "PENDING",
  status_reason: null,
  entry: "1498.10",
  stop: "1485.25",
  target: "1529.00",
  quantity: 33,
  risk_amount: "424.05",
  rr: "2.4047",
  note: null,
  setup_type: "OPENING_RANGE_BREAKOUT",
  created_at: "2026-11-18T11:00:30+05:30",
  updated_at: "2026-11-18T11:00:30+05:30",
  linked: { actual_trade_ids: [] },
};

describe("mapTradePlan", () => {
  it("shows the plan number, keeps the server id and converts decimals", () => {
    const p = mapTradePlan(api);
    expect([p.id, p.apiId, p.symbol, p.setupType, p.status, p.signal]).toEqual(["TP-0001", "uuid-1", "RELIANCE", "opening-range-breakout", "pending", "buy-watch"]);
    expect([p.entry, p.stopLoss, p.target, p.riskReward, p.quantity, p.riskAmount]).toEqual([1498.1, 1485.25, 1529, 2.4047, 33, 424.05]);
    expect(p.linkedOrderId).toBeUndefined();
  });

  it("maps every backend status and the manual plan", () => {
    const s = (status: string) => mapTradePlan({ ...api, status }).status;
    expect([s("TRIGGERED"), s("FILLED"), s("EXPIRED"), s("INVALIDATED"), s("SKIPPED"), s("CANCELLED")]).toEqual([
      "entry-confirmed", "active", "invalidated", "invalidated", "invalidated", "cancelled",
    ]);
    expect(mapTradePlan({ ...api, setup_type: null }).setupType).toBeNull();
    expect(mapTradePlan({ ...api, linked: { actual_trade_ids: ["t1"] } }).linkedOrderId).toBe("t1");
  });
});

describe("apiSetupType", () => {
  it("reverses the scanner mapping", () => {
    expect(apiSetupType("opening-range-breakout")).toBe("OPENING_RANGE_BREAKOUT");
    expect(apiSetupType("breakout-retest")).toBe("BREAKOUT_RETEST");
    expect(apiSetupType("range-bound")).toBeNull();
  });
});

describe("validatePlanLevels", () => {
  it("accepts a long plan", () => {
    expect(validatePlanLevels({ entry: "1498.10", stop: "1485.25", target: "1529" })).toEqual({});
  });

  it("flags a stop at or above entry, a target at or below it and bad prices", () => {
    expect(validatePlanLevels({ entry: "100", stop: "100", target: "110" }).stop).toBeDefined();
    expect(validatePlanLevels({ entry: "100", stop: "95", target: "100" }).target).toBeDefined();
    expect(Object.keys(validatePlanLevels({ entry: "x", stop: "0", target: "1.234" })).sort()).toEqual(["entry", "stop", "target"]);
  });
});
