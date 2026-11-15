/**
 * SAMPLE DATA GENERATOR.
 *
 * Builds deterministic daily OHLCV series from scripted price-action
 * templates (breakout/retest, pullback, range, breakdown). The output is
 * illustrative only and exists so the UI can be demonstrated end-to-end.
 * It will be replaced by market data from the backend.
 */
import type { Candle } from "@/types";
import { hashString, mulberry32, toTick } from "./rng";
import { SAMPLE_AS_OF, type DemoTemplate, type UniverseEntry } from "./universe";

export const SERIES_LENGTH = 240;

interface Segment {
  bars: number;
  /** Ratio target at the end of the segment (start of series = 1.0). */
  to: number;
  vol?: number;
}

export interface ZoneSpec {
  kind: "support" | "resistance";
  low: number;
  high: number;
  label: string;
  touches: number;
  strength: "weak" | "moderate" | "strong";
  /** Segment index whose END marks where the zone starts being drawn. */
  fromSeg: number;
}

export interface TemplateSpec {
  segments: Segment[];
  zones: ZoneSpec[];
  /** Segment indices with special meaning for event detection. */
  marks: Record<string, number>;
  /** Ratio constants used to derive levels. */
  refs: Record<string, number>;
}

/** Bullish breakout above a multi-touch resistance, followed by a retest. */
function breakoutTemplate(rnd: () => number): TemplateSpec {
  const finish = 1.058 + rnd() * 0.035;
  return {
    segments: [
      { bars: 25, to: 0.92 },
      { bars: 12, to: 0.96 },
      { bars: 15, to: 0.88 },
      { bars: 14, to: 0.97, vol: 1.2 },
      { bars: 10, to: 0.93, vol: 0.8 },
      { bars: 16, to: 1.04, vol: 1.1 },
      { bars: 12, to: 0.99, vol: 0.8 },
      { bars: 14, to: 1.045 },
      { bars: 12, to: 1.0, vol: 0.75 },
      { bars: 10, to: 1.04 },
      { bars: 8, to: 1.1, vol: 2.1 },
      { bars: 8, to: 1.052, vol: 0.7 },
      { bars: 6, to: finish, vol: 1.1 },
    ],
    zones: [
      { kind: "support", low: 1.03, high: 1.05, label: "Breakout zone · prior resistance", touches: 4, strength: "strong", fromSeg: 5 },
      { kind: "support", low: 0.985, high: 1.0, label: "Higher-low demand", touches: 2, strength: "moderate", fromSeg: 6 },
    ],
    marks: { breakout: 10, retest: 11, base: 2 },
    refs: { zoneHigh: 1.05, zoneLow: 1.03, baseLow: 0.88 },
  };
}

/** Established uptrend pulling back into a prior breakout level. */
function pullbackTemplate(rnd: () => number): TemplateSpec {
  const finish = 1.093 + rnd() * 0.022;
  return {
    segments: [
      { bars: 20, to: 0.93 },
      { bars: 16, to: 1.03, vol: 1.2 },
      { bars: 10, to: 0.99, vol: 0.8 },
      { bars: 16, to: 1.09, vol: 1.3 },
      { bars: 12, to: 1.045, vol: 0.8 },
      { bars: 16, to: 1.155, vol: 1.2 },
      { bars: 12, to: finish, vol: 0.7 },
    ],
    zones: [
      { kind: "support", low: 1.075, high: 1.095, label: "Prior swing high · now support", touches: 2, strength: "strong", fromSeg: 3 },
      { kind: "resistance", low: 1.14, high: 1.16, label: "Recent swing high", touches: 1, strength: "moderate", fromSeg: 5 },
    ],
    marks: { impulse: 5, pullback: 6 },
    refs: { zoneHigh: 1.095, zoneLow: 1.075, lastHL: 1.045, swingHigh: 1.155 },
  };
}

/** Horizontal range with repeated tests of both boundaries. */
function rangeTemplate(rnd: () => number): TemplateSpec {
  const finish = 0.985 + rnd() * 0.04;
  return {
    segments: [
      { bars: 24, to: 1.05, vol: 1.2 },
      { bars: 12, to: 0.955 },
      { bars: 12, to: 1.045 },
      { bars: 11, to: 0.96 },
      { bars: 12, to: 1.05 },
      { bars: 12, to: 0.952 },
      { bars: 13, to: 1.043 },
      { bars: 11, to: 0.962 },
      { bars: 12, to: 1.048 },
      { bars: 10, to: finish, vol: 0.8 },
    ],
    zones: [
      { kind: "resistance", low: 1.035, high: 1.055, label: "Range high", touches: 4, strength: "strong", fromSeg: 0 },
      { kind: "support", low: 0.945, high: 0.965, label: "Range low", touches: 4, strength: "strong", fromSeg: 1 },
    ],
    marks: {},
    refs: { resLow: 1.035, supHigh: 0.965, supLow: 0.945 },
  };
}

/** Mirror image of the breakout template: support fails, then is retested. */
function breakdownTemplate(rnd: () => number): TemplateSpec {
  const base = breakoutTemplate(rnd);
  const m = (r: number) => 2 - r;
  return {
    segments: base.segments.map((s) => ({ ...s, to: m(s.to) })),
    zones: [
      { kind: "resistance", low: m(1.05), high: m(1.03), label: "Breakdown zone · prior support", touches: 4, strength: "strong", fromSeg: 5 },
      { kind: "resistance", low: m(1.0), high: m(0.985), label: "Lower-high supply", touches: 2, strength: "moderate", fromSeg: 6 },
    ],
    marks: { breakdown: 10, retest: 11, base: 2 },
    refs: { zoneLow: m(1.05), zoneHigh: m(1.03), baseHigh: m(0.88) },
  };
}

const TEMPLATES: Record<DemoTemplate, (rnd: () => number) => TemplateSpec> = {
  breakout: breakoutTemplate,
  pullback: pullbackTemplate,
  range: rangeTemplate,
  breakdown: breakdownTemplate,
};

/** Trading days (Mon–Fri) ending at `end`, oldest first. Holidays are ignored in sample data. */
export function tradingDays(count: number, end = SAMPLE_AS_OF) {
  const out: string[] = [];
  const d = new Date(`${end}T00:00:00Z`);
  while (out.length < count) {
    const day = d.getUTCDay();
    if (day !== 0 && day !== 6) out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return out.reverse();
}

export interface GeneratedSeries {
  candles: Candle[];
  spec: TemplateSpec;
  /** Index into candles where each template segment ends. */
  segmentEnds: number[];
  /** Multiplier from ratio units to ₹. */
  scale: number;
}

const ease = (t: number) => 0.5 * t + 0.5 * t * t * (3 - 2 * t);

export function generateSeries(entry: UniverseEntry): GeneratedSeries {
  const rnd = mulberry32(hashString(entry.symbol));
  const spec = TEMPLATES[entry.template](rnd);

  // Lead-in drift so every series has SERIES_LENGTH bars.
  const templBars = spec.segments.reduce((a, s) => a + s.bars, 0);
  const leadBars = Math.max(0, SERIES_LENGTH - templBars);
  const leadStart = 1 + (rnd() - 0.4) * 0.12;
  const leadSegs: Segment[] = [];
  let remaining = leadBars;
  let lvl = leadStart;
  while (remaining > 0) {
    const bars = Math.min(remaining, 14 + Math.floor(rnd() * 10));
    const next = remaining - bars <= 0 ? 1 : lvl * (1 + (rnd() - 0.5) * 0.09);
    leadSegs.push({ bars, to: next, vol: 0.9 });
    lvl = next;
    remaining -= bars;
  }
  const allSegs = [...leadSegs, ...spec.segments];

  const noiseAmp = 0.0055;
  const wickAmp = 0.0065;
  const raw: Omit<Candle, "time">[] = [];
  const segmentEnds: number[] = [];
  let from = leadStart;
  let prevClose = leadStart;

  for (const seg of allSegs) {
    for (let i = 1; i <= seg.bars; i++) {
      const t = i / seg.bars;
      const target = from + (seg.to - from) * ease(t);
      const close = target * (1 + (rnd() - 0.5) * 2 * noiseAmp);
      const open = prevClose * (1 + (rnd() - 0.5) * 0.006);
      const high = Math.max(open, close) * (1 + rnd() * wickAmp);
      const low = Math.min(open, close) * (1 - rnd() * wickAmp);
      const volume = entry.avgVolume * (0.65 + rnd() * 0.7) * (seg.vol ?? 1);
      raw.push({ open, high, low, close, volume });
      prevClose = close;
    }
    from = seg.to;
    segmentEnds.push(raw.length - 1);
  }

  const scale = entry.price / raw[raw.length - 1].close;
  const days = tradingDays(raw.length);
  const candles: Candle[] = raw.map((c, i) => ({
    time: days[i],
    open: toTick(c.open * scale),
    high: toTick(c.high * scale),
    low: toTick(c.low * scale),
    close: toTick(c.close * scale),
    volume: Math.round(c.volume),
  }));
  // Pin the final close exactly to the universe price.
  candles[candles.length - 1].close = entry.price;
  candles[candles.length - 1].high = Math.max(candles[candles.length - 1].high, entry.price);
  candles[candles.length - 1].low = Math.min(candles[candles.length - 1].low, entry.price);

  // Re-index segment ends to the template's own segments (drop lead-in).
  const templateEnds = segmentEnds.slice(leadSegs.length);
  return { candles, spec, segmentEnds: templateEnds, scale };
}
