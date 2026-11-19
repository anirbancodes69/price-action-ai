import { describe, expect, it } from "vitest";
import { mapPosition, mapTrade, nowIstLocal, validateFill, type ApiActualTrade, type FillForm } from "./trades";

const trade: ApiActualTrade = {
  id: "t1",
  instrument: { symbol: "RELIANCE", name: "Reliance Industries" },
  trade_plan_id: null,
  status: "OPEN",
  quantity_open: 6,
  avg_entry_price: "100.00",
  avg_exit_price: "110.00",
  realized_pnl: "40.00",
  charges: "8.00",
  fills: [{ id: "f1", side: "BUY", quantity: 10, price: "100.00", executed_at: "2026-11-18T10:00:00+05:30", fees: null }],
};

const form: FillForm = { symbol: "reliance", side: "BUY", quantity: "10", price: "1498.10", executedAt: "2026-11-18T10:00", fees: "" };

describe("mapTrade", () => {
  it("converts decimals and nets the charges off the realised P&L", () => {
    const t = mapTrade(trade);
    expect([t.symbol, t.quantityOpen, t.avgEntry, t.avgExit]).toEqual(["RELIANCE", 6, 100, 110]);
    expect([t.realisedPnl, t.charges, t.netRealisedPnl]).toEqual([40, 8, 32]);
    expect(t.fills[0]).toMatchObject({ side: "BUY", price: 100, fees: null });
  });

  it("has no realised P&L before the first sell", () => {
    const t = mapTrade({ ...trade, realized_pnl: null, charges: "5.00", avg_exit_price: null });
    expect([t.realisedPnl, t.netRealisedPnl, t.avgExit]).toEqual([null, null, null]);
  });
});

describe("mapPosition", () => {
  it("keeps a missing price, stop and target as null instead of zero", () => {
    const p = mapPosition({
      position_id: "p1", symbol: "AAA", quantity: 3, entry_price: "50.00", entry_at: "2026-11-18T10:00:00+05:30",
      current_price: null, price_at: null, unrealised_pnl: null, stop: null, target: null,
    });
    expect([p.currentPrice, p.unrealisedPnl, p.stop, p.target]).toEqual([null, null, null, null]);
    expect(p.entryPrice).toBe(50);
  });
});

describe("validateFill", () => {
  it("accepts a complete form", () => {
    expect(validateFill(form, true)).toEqual({});
    expect(validateFill({ ...form, symbol: "", fees: "12.50" }, false)).toEqual({});
  });

  it("flags each bad field", () => {
    const e = validateFill({ symbol: "bad symbol!", side: "BUY", quantity: "0", price: "1.234", executedAt: "", fees: "x" }, true);
    expect(Object.keys(e).sort()).toEqual(["executedAt", "fees", "price", "quantity", "symbol"]);
  });

  it("rejects a zero price and a fractional quantity", () => {
    expect(validateFill({ ...form, price: "0" }, true).price).toBeDefined();
    expect(validateFill({ ...form, quantity: "1.5" }, true).quantity).toBeDefined();
  });
});

describe("nowIstLocal", () => {
  it("reads the IST wall clock", () => {
    expect(nowIstLocal(Date.parse("2026-11-18T05:30:00Z"))).toBe("2026-11-18T11:00");
    expect(nowIstLocal(Date.parse("2026-11-18T20:00:00Z"))).toBe("2026-11-19T01:30");
  });
});
