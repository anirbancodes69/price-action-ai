import { describe, expect, it } from "vitest";
import { chartTime, isIntraday, sessionStarts } from "./time";

describe("chart time", () => {
  it("keeps daily bars as business days", () => {
    expect(isIntraday("2026-11-13")).toBe(false);
    expect(chartTime("2026-11-13")).toBe("2026-11-13");
  });

  it("shifts intraday bars so the UTC axis reads IST", () => {
    // 09:15 IST is 03:45 UTC; shifted by +05:30 the chart shows 09:15.
    const t = chartTime("2026-11-13T09:15:00+05:30") as number;
    expect(new Date(t * 1000).toISOString()).toBe("2026-11-13T09:15:00.000Z");
    expect(chartTime("2026-11-13T09:20:00+05:30") as number).toBe(t + 300);
  });

  it("finds the first bar of each new session", () => {
    const bar = (time: string) => ({ time, open: 1, high: 1, low: 1, close: 1, volume: 0 });
    const candles = [
      bar("2026-11-12T15:20:00+05:30"),
      bar("2026-11-12T15:25:00+05:30"),
      bar("2026-11-13T09:15:00+05:30"),
      bar("2026-11-13T09:20:00+05:30"),
    ];
    expect(sessionStarts(candles)).toEqual(["2026-11-13T09:15:00+05:30"]);
    expect(sessionStarts(candles.slice(0, 2))).toEqual([]);
  });
});
