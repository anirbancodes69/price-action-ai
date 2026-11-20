import { describe, expect, it, vi } from "vitest";
import { analysisProblem, fetchAnalysis, mapAnalysis, type ApiAnalysisRun } from "./analysis";

const setup = {
  id: "s1",
  type: "OPENING_RANGE_BREAKOUT",
  direction: "LONG" as const,
  informational: false,
  status: "ENTRY_CONFIRMED",
  levels: { trigger: "1496.50", entry: "1498.10", stop: "1485.25", target: "1529.00", rr: "2.4046", target_source: "ZONE" },
  quality: { score: 90, version: "paqs-intraday-0.1.0", components: [{ key: "structure", label: "structure", points: 20, max: 25, missing: false }] },
};

const run: ApiAnalysisRun = {
  id: "r1",
  instrument: { symbol: "RELIANCE", name: "Reliance Industries", exchange: "NSE" },
  as_of: "2026-11-18T11:00:00+05:30",
  status: "COMPLETED",
  context: {
    htf_state: "SIDEWAYS",
    session: {
      pdh: "1500.00", pdl: "1470.00", pdc: "1480.00", or_high: "1496.50", or_low: null,
      session_high: "1499.00", session_low: "1486.00",
      entry_cutoff_at: "2026-11-18T14:45:00+05:30", session_end_exit_at: "2026-11-18T15:15:00+05:30",
    },
  },
  structure: { state: "BULLISH", transition_direction: null },
  signal: { state: "ENTRY_CONFIRMED", reason_codes: [], signal_at: "2026-11-18T11:00:00+05:30", valid_until: "2026-11-18T11:05:00+05:30" },
  primary_setup_id: "s1",
  setups: [setup],
  swings: [
    { kind: "LOW", bar_start: "2026-11-18T09:30:00+05:30", price: "1486.00", label: "HL" },
    { kind: "HIGH", bar_start: "2026-11-18T09:45:00+05:30", price: "1490.00", label: "EQH" },
  ],
  events: [
    { type: "BOS", direction: "UP", level: "1496.50", level_bar_start: "2026-11-18T09:35:00+05:30", break_bar_start: "2026-11-18T10:50:00+05:30" },
    { type: "WICK_BREACH", direction: "UP", level: "1500.00", level_bar_start: "2026-11-18T09:35:00+05:30", break_bar_start: "2026-11-18T10:55:00+05:30" },
  ],
  zones: [{ id: "z1", role: "SUPPORT", low: "1485.00", high: "1488.00", touches: 3, strength_bucket: "STRONG", formed_at: "2026-11-18T09:50:00+05:30" }],
  candles: [
    { start: "2026-11-18T10:50:00+05:30", open: "1496.00", high: "1498.00", low: "1495.50", close: "1497.00", volume: 100 },
    { start: "2026-11-18T10:55:00+05:30", open: "1497.00", high: "1499.00", low: "1496.50", close: "1498.10", volume: 150 },
  ],
};

describe("mapAnalysis", () => {
  it("maps the engine vocabulary and converts decimal strings without recomputing levels", () => {
    const a = mapAnalysis(run);
    expect(a.levels).toEqual({ entry: 1498.1, stopLoss: 1485.25, target: 1529, riskReward: 2.4046 });
    expect(a.setup).toMatchObject({ type: "opening-range-breakout", status: "entry-confirmed", signal: "entry-confirmed", direction: "long" });
    expect([a.structure, a.htfStructure, a.bias]).toEqual(["uptrend", "range", "bullish"]);
    expect(a.qualityScore).toBe(90);
    expect(a.qualityFactors).toEqual([{ label: "structure", score: 80, note: "20 of 25 points" }]);
    expect([a.signalAt, a.validUntil]).toEqual([run.signal.signal_at, run.signal.valid_until]);
  });

  it("uses the last 5m close as the price and the previous-day close for the change", () => {
    const a = mapAnalysis(run);
    expect(a.stock.price).toBe(1498.1);
    expect(a.stock.change).toBeCloseTo(18.1, 6);
    expect(a.stock.volume).toBe(250);
    expect(a.intraday["5m"]).toHaveLength(2);
    expect(a.intraday["15m"]).toEqual([]);
    expect(a.candles).toEqual([]);
  });

  it("keeps only drawable swings and structure breaks", () => {
    const a = mapAnalysis(run);
    expect(a.swings.map((s) => s.label)).toEqual(["HL"]); // EQH has no frontend label
    expect(a.breaks).toEqual([
      { kind: "BOS", direction: "bullish", level: 1496.5, fromTime: "2026-11-18T09:35:00+05:30", toTime: "2026-11-18T10:50:00+05:30" },
    ]);
    expect(a.zones[0]).toMatchObject({ kind: "support", strength: "strong", low: 1485, high: 1488, touches: 3 });
  });

  it("has no levels and no setup details for a no-trade analysis", () => {
    const a = mapAnalysis({ ...run, primary_setup_id: null, setups: [], signal: { ...run.signal, state: "NO_TRADE", signal_at: null, valid_until: null } });
    expect(a.levels).toBeNull();
    expect(a.setup.signal).toBe("no-trade");
    expect(a.setup.type).toBe("range-bound");
    expect(a.qualityFactors).toEqual([]);
    expect(a.entryConditions).toEqual([]);
  });

  it("keeps the opening range open while it forms", () => {
    const a = mapAnalysis(run);
    expect([a.session.orHigh, a.session.orLow]).toEqual([1496.5, null]);
  });
});

describe("mapAnalysis evidence", () => {
  it("restates quality components and engine reason codes, applying no threshold", () => {
    const comps = [
      { key: "a", label: "Structure", points: 20, max: 25, missing: false },
      { key: "b", label: "Volume", points: 0, max: 10, missing: false },
      { key: "c", label: "Context", points: 0, max: 10, missing: true },
    ];
    const a = mapAnalysis({
      ...run,
      setups: [{ ...setup, quality: { ...setup.quality, components: comps } }],
      signal: { ...run.signal, state: "NO_TRADE", reason_codes: ["LOW_SCORE", "SOMETHING_NEW"] },
    });
    expect(a.evidence).toEqual([
      { title: "Structure", detail: "20 of 25 points.", tone: "supporting" },
      { title: "Volume", detail: "0 of 10 points.", tone: "caution" },
      { title: "Context", detail: "Not available for this bar.", tone: "caution" },
      { title: "The quality score is below the minimum", detail: "Reported by the engine.", tone: "caution" },
      { title: "SOMETHING_NEW", detail: "Reported by the engine.", tone: "caution" },
    ]);
  });

  it("has no evidence without a setup or reasons", () => {
    expect(mapAnalysis({ ...run, primary_setup_id: null, setups: [] }).evidence).toEqual([]);
  });
});

describe("mapAnalysis series", () => {
  it("maps 15m bars as timestamps and daily bars as session dates", () => {
    const bar = { start: "2026-11-17T09:15:00+05:30", open: "1.00", high: "2.00", low: "0.50", close: "1.50", volume: 5 };
    const a = mapAnalysis({ ...run, candles_15m: [bar], candles_1d: [bar] });
    expect(a.intraday["15m"][0]).toEqual({ time: "2026-11-17T09:15:00+05:30", open: 1, high: 2, low: 0.5, close: 1.5, volume: 5 });
    expect(a.candles[0].time).toBe("2026-11-17");
  });
});

describe("analysisProblem", () => {
  it("reports runs that cannot be drawn", () => {
    expect(analysisProblem(run)).toBeNull();
    expect(analysisProblem({ ...run, status: "INSUFFICIENT_HISTORY" })).toMatch(/Not enough/);
    expect(analysisProblem({ ...run, context: { ...run.context, session: null } })).toMatch(/not available/);
  });
});

describe("fetchAnalysis", () => {
  it("asks for the 5m, 15m and daily bars, so every chart timeframe has data", async () => {
    const urls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        urls.push(url);
        return new Response(JSON.stringify({ data: run, meta: { request_id: "r", data_mode: "PERSONAL" } }), { status: 200, headers: { "Content-Type": "application/json" } });
      }),
    );

    const { meta } = await fetchAnalysis("M&M");

    expect(urls).toEqual(["/api/v1/analysis/M%26M?include=candles,candles_15m,candles_1d"]);
    expect(meta.dataMode).toBe("PERSONAL");
    vi.unstubAllGlobals();
  });
});
