import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { generateSeries } from "./demo-series";
import { BARS_5M, fifteenMinuteBars, fiveMinuteBars } from "./demo-intraday";
import { UNIVERSE } from "./universe";
import fixture from "./fixtures/intraday-parity.json";

/**
 * The TypeScript sample generator must equal the PHP seeder (`DemoIntradayGenerator.php`) bar for bar, so the UI's
 * sample bars and the seeded DEMO bars agree. Fixture exported from the PHP generator; regenerate only if it changes.
 */
const fmt = (v: number) => {
  const s = v.toFixed(2);
  return s.replace(/\.?0+$/, "");
};
const line = (b: { time: string; open: number; high: number; low: number; close: number; volume: number }) =>
  [b.time, fmt(b.open), fmt(b.high), fmt(b.low), fmt(b.close), b.volume].join(",");
const sha = (lines: string[]) => createHash("sha256").update(lines.join("\n")).digest("hex");

describe("demo intraday generator", () => {
  it("matches the PHP seeder for every demo symbol", () => {
    const symbols = fixture.symbols as Record<string, { bars5m: number; first5m: string; last5m: string; sha5m: string; sha15m: string }>;
    expect(Object.keys(symbols)).toHaveLength(UNIVERSE.length);
    for (const entry of UNIVERSE) {
      const daily = generateSeries(entry).candles.slice(-fixture.sessions);
      const five = daily.flatMap((d) => fiveMinuteBars(entry.symbol, d));
      const fifteen = daily.flatMap((d) => fifteenMinuteBars(fiveMinuteBars(entry.symbol, d)));
      const lines = five.map(line);
      const expected = symbols[entry.symbol];
      expect(five).toHaveLength(expected.bars5m);
      expect(lines[0]).toBe(expected.first5m);
      expect(lines[lines.length - 1]).toBe(expected.last5m);
      expect(sha(lines)).toBe(expected.sha5m);
      expect(sha(fifteen.map(line))).toBe(expected.sha15m);
    }
  });

  it("keeps every session consistent with its daily bar", () => {
    const entry = UNIVERSE[0];
    for (const d of generateSeries(entry).candles.slice(-3)) {
      const bars = fiveMinuteBars(entry.symbol, d);
      expect(bars).toHaveLength(BARS_5M);
      expect(bars[0].open).toBe(d.open);
      expect(bars[BARS_5M - 1].close).toBe(d.close);
      expect(Math.max(...bars.map((b) => b.high))).toBe(d.high);
      expect(Math.min(...bars.map((b) => b.low))).toBe(d.low);
      expect(bars.reduce((s, b) => s + b.volume, 0)).toBe(d.volume);
      expect(bars[0].time).toBe(`${d.time}T09:15:00+05:30`);
      expect(bars[BARS_5M - 1].time).toBe(`${d.time}T15:25:00+05:30`);
    }
  });
});
