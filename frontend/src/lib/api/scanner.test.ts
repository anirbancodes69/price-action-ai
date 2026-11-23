import { describe, expect, it } from "vitest";
import { mapScannerRow, type ApiScannerRow } from "./scanner";

const base: ApiScannerRow = {
  instrument: { symbol: "RELIANCE", name: "Reliance Industries", exchange: "NSE", sector: null },
  last_close: "1498.10",
  change: "18.10",
  change_pct: "1.2229",
  as_of: "2026-11-18T15:25:00+05:30",
  htf_state: "BULLISH",
  structure_state: "BULLISH",
  signal_state: "ENTRY_CONFIRMED",
  signal_at: "2026-11-18T15:25:00+05:30",
  valid_until: "2026-11-18T15:30:00+05:30",
  primary_setup: {
    type: "OPENING_RANGE_BREAKOUT",
    direction: "LONG",
    status: "ENTRY_CONFIRMED",
    levels: { trigger: "1496.50", entry: "1498.10", stop: "1485.25", target: "1529.00", rr: "2.4046", target_source: "ZONE" },
    quality_score: 90,
  },
};

describe("mapScannerRow", () => {
  it("maps the canonical vocabulary to the frontend vocabulary (TRD-04 §13)", () => {
    const r = mapScannerRow(base);
    expect(r.structure).toBe("uptrend");
    expect(r.htfStructure).toBe("uptrend");
    expect(r.bias).toBe("bullish");
    expect(r.setupType).toBe("opening-range-breakout");
    expect(r.setupStatus).toBe("entry-confirmed");
    expect(r.signal).toBe("entry-confirmed");
    expect(r.direction).toBe("long");
    expect(r.qualityScore).toBe(90);
  });

  it("converts decimal strings to display numbers without recomputing anything", () => {
    const r = mapScannerRow(base);
    expect(r.levels).toEqual({ entry: 1498.1, stopLoss: 1485.25, target: 1529, riskReward: 2.4046 });
    expect([r.stock.price, r.stock.change, r.stock.changePct]).toEqual([1498.1, 18.1, 1.2229]);
    expect([r.signalAt, r.validUntil]).toEqual([base.signal_at, base.valid_until]);
  });

  it("represents no-trade as a valid row: no levels, range-bound, neutral", () => {
    const r = mapScannerRow({
      ...base,
      htf_state: null,
      structure_state: null,
      signal_state: "NO_TRADE",
      primary_setup: null,
      change: null,
      change_pct: null,
    });
    expect(r.levels).toBeNull();
    expect(r.setupStatus).toBeNull(); // no "Detected" badge for a row that has no setup
    expect(r.setupType).toBe("range-bound");
    expect(r.signal).toBe("no-trade");
    expect([r.structure, r.bias, r.htfStructure]).toEqual(["range", "neutral", "range"]);
    expect([r.stock.change, r.stock.changePct]).toEqual([0, 0]);
  });

  it("keeps a SHORT setup as informational direction and maps statuses", () => {
    const r = mapScannerRow({
      ...base,
      signal_state: "NO_TRADE",
      primary_setup: { ...base.primary_setup!, type: "PREV_DAY_LOW_BREAK", direction: "SHORT", status: "EXPIRED", levels: null },
    });
    expect([r.direction, r.setupType, r.setupStatus, r.levels]).toEqual(["short", "prev-day-low-break", "expired", null]);
  });

  it("shows every engine-emittable setup type as itself, never as range-bound (Phase 1 P4)", () => {
    const sweep = mapScannerRow({ ...base, primary_setup: { ...base.primary_setup!, type: "LIQUIDITY_SWEEP_REVERSAL" } });
    const reclaim = mapScannerRow({ ...base, primary_setup: { ...base.primary_setup!, type: "FAILED_BREAKDOWN_RECLAIM" } });
    expect([sweep.setupType, reclaim.setupType]).toEqual(["liquidity-sweep-reversal", "failed-breakdown-reclaim"]);
  });

  it("falls back safely for a setup type the frontend does not know", () => {
    const r = mapScannerRow({ ...base, primary_setup: { ...base.primary_setup!, type: "SOMETHING_NEW" } });
    expect(r.setupType).toBe("range-bound");
  });
});
