/**
 * SAMPLE ANALYSIS BUILDER.
 *
 * Produces a StockAnalysis for the demo from generated sample candles.
 * The swing/structure detection here is a simple illustrative heuristic so
 * the chart annotations line up with the sample bars. It is NOT the
 * product's trading logic — that will be supplied by the Python analysis
 * engine and returned through the same `StockAnalysis` contract.
 */
import type {
  Bias,
  Candle,
  ChartEvent,
  EvidenceItem,
  MarketStructure,
  PriceZone,
  QualityFactor,
  SetupStatus,
  SetupType,
  SignalState,
  Stock,
  StockAnalysis,
  StructureBreak,
  SwingPoint,
  TradeLevels,
} from "@/types";
import { formatDate, formatPrice } from "@/lib/format";
import { clamp } from "@/lib/utils";
import { toTick } from "./rng";
import { generateSeries, type GeneratedSeries } from "./demo-series";
import { intradayFor, sessionLevelsFor } from "./demo-session";
import { SAMPLE_AS_OF, SAMPLE_AS_OF_TS, UNIVERSE, type UniverseEntry } from "./universe";

const ZIGZAG_THRESHOLD = 0.03;

interface Pivot {
  index: number;
  confirmIndex: number;
  price: number;
  kind: "high" | "low";
}

function zigzag(c: Candle[], th: number): Pivot[] {
  const pivots: Pivot[] = [];
  let trend: "up" | "down" | null = null;
  let hi = 0;
  let lo = 0;
  for (let i = 1; i < c.length; i++) {
    if (trend === null) {
      if (c[i].high > c[hi].high) hi = i;
      if (c[i].low < c[lo].low) lo = i;
      if (c[hi].high / c[lo].low - 1 >= th) {
        if (lo < hi) {
          pivots.push({ index: lo, confirmIndex: i, price: c[lo].low, kind: "low" });
          trend = "up";
        } else {
          pivots.push({ index: hi, confirmIndex: i, price: c[hi].high, kind: "high" });
          trend = "down";
        }
      }
    } else if (trend === "up") {
      if (c[i].high > c[hi].high) hi = i;
      else if (c[i].low <= c[hi].high * (1 - th)) {
        pivots.push({ index: hi, confirmIndex: i, price: c[hi].high, kind: "high" });
        trend = "down";
        lo = i;
      }
    } else {
      if (c[i].low < c[lo].low) lo = i;
      else if (c[i].high >= c[lo].low * (1 + th)) {
        pivots.push({ index: lo, confirmIndex: i, price: c[lo].low, kind: "low" });
        trend = "up";
        hi = i;
      }
    }
  }
  return pivots;
}

function labelSwings(c: Candle[], pivots: Pivot[]): SwingPoint[] {
  const out: SwingPoint[] = [];
  let lastHigh: number | null = null;
  let lastLow: number | null = null;
  for (const p of pivots) {
    if (p.kind === "high") {
      if (lastHigh !== null) {
        out.push({ time: c[p.index].time, price: p.price, kind: "high", label: p.price > lastHigh ? "HH" : "LH" });
      }
      lastHigh = p.price;
    } else {
      if (lastLow !== null) {
        out.push({ time: c[p.index].time, price: p.price, kind: "low", label: p.price > lastLow ? "HL" : "LL" });
      }
      lastLow = p.price;
    }
  }
  return out;
}

function detectBreaks(c: Candle[], pivots: Pivot[]): StructureBreak[] {
  const breaks: StructureBreak[] = [];
  let trend: "up" | "down" | null = null;
  let hi: (Pivot & { broken: boolean }) | null = null;
  let lo: (Pivot & { broken: boolean }) | null = null;
  for (let i = 0; i < c.length; i++) {
    for (const p of pivots) {
      if (p.confirmIndex !== i) continue;
      if (p.kind === "high") hi = { ...p, broken: false };
      else lo = { ...p, broken: false };
    }
    if (hi && !hi.broken && c[i].close > hi.price) {
      breaks.push({
        kind: trend === "down" ? "CHoCH" : "BOS",
        direction: "bullish",
        level: hi.price,
        fromTime: c[hi.index].time,
        toTime: c[i].time,
      });
      trend = "up";
      hi.broken = true;
    }
    if (lo && !lo.broken && c[i].close < lo.price) {
      breaks.push({
        kind: trend === "up" ? "CHoCH" : "BOS",
        direction: "bearish",
        level: lo.price,
        fromTime: c[lo.index].time,
        toTime: c[i].time,
      });
      trend = "down";
      lo.broken = true;
    }
  }
  // Earliest break has no prior trend to change — keep the last few for readability.
  return breaks.slice(1).slice(-6);
}

function classify(swings: SwingPoint[], breaks: StructureBreak[]): MarketStructure {
  const lastHigh = [...swings].reverse().find((s) => s.kind === "high");
  const lastLow = [...swings].reverse().find((s) => s.kind === "low");
  if (lastHigh?.label === "HH" && lastLow?.label === "HL") return "uptrend";
  if (lastHigh?.label === "LH" && lastLow?.label === "LL") return "downtrend";
  if (breaks.at(-1)?.kind === "CHoCH") return "transition";
  return "range";
}

/* ---------- helpers over the generated series ---------- */

function segRange(g: GeneratedSeries, seg: number): [number, number] {
  const end = g.segmentEnds[seg];
  const start = end - g.spec.segments[seg].bars + 1;
  return [start, end];
}

function minLow(c: Candle[], a: number, b: number) {
  let idx = a;
  for (let i = a; i <= b; i++) if (c[i].low < c[idx].low) idx = i;
  return idx;
}

function maxHigh(c: Candle[], a: number, b: number) {
  let idx = a;
  for (let i = a; i <= b; i++) if (c[i].high > c[idx].high) idx = i;
  return idx;
}

function avgVolume(c: Candle[], end: number, n = 20) {
  const slice = c.slice(Math.max(0, end - n), end);
  return slice.reduce((a, x) => a + x.volume, 0) / Math.max(1, slice.length);
}

function rr(entry: number, stop: number, target: number) {
  const risk = Math.abs(entry - stop);
  return risk === 0 ? 0 : Math.round((Math.abs(target - entry) / risk) * 10) / 10;
}

function scoreRR(r: number) {
  return clamp(Math.round(30 + r * 22), 20, 98);
}

/* ---------- per-template setup construction ---------- */

interface SetupBuild {
  type: SetupType;
  direction: "long" | "short";
  status: SetupStatus;
  signal: SignalState;
  headline: string;
  levels: TradeLevels;
  events: ChartEvent[];
  entryConditions: string[];
  invalidation: string[];
  evidence: EvidenceItem[];
  volumeRatio: number;
}

function buildBreakout(g: GeneratedSeries): SetupBuild {
  const c = g.candles;
  const s = g.scale;
  const zoneHigh = toTick(g.spec.refs.zoneHigh * s);
  const zoneLow = toTick(g.spec.refs.zoneLow * s);
  const [boA, boB] = segRange(g, g.spec.marks.breakout);
  const [rtA] = segRange(g, g.spec.marks.retest);
  const last = c.length - 1;

  let boIdx = boA;
  for (let i = boA; i <= boB; i++) if (c[i].close > zoneHigh) { boIdx = i; break; }
  const peakIdx = maxHigh(c, boA, boB);
  const retestIdx = minLow(c, rtA, last);
  const triggerIdx = maxHigh(c, retestIdx, last - 1);
  const trigger = c[triggerIdx].high;
  const confirmed = c[last].close > trigger;

  const entry = toTick(trigger * 1.001);
  const stopLoss = toTick(c[retestIdx].low * 0.994);
  const baseLow = toTick(g.spec.refs.baseLow * s);
  const target = toTick(zoneHigh + (zoneHigh - baseLow) * 0.75);
  const volumeRatio = c[boIdx].volume / avgVolume(c, boIdx);

  return {
    type: "breakout-retest",
    direction: "long",
    status: confirmed ? "entry-confirmed" : "awaiting-confirmation",
    signal: confirmed ? "entry-confirmed" : "buy-watch",
    headline: confirmed
      ? "Retest held and price closed above the post-retest high."
      : "Breakout retested the prior resistance zone; waiting for a close above the retest high.",
    levels: { entry, stopLoss, target, riskReward: rr(entry, stopLoss, target) },
    events: [
      { kind: "breakout", time: c[boIdx].time, price: c[boIdx].close, label: "Breakout" },
      { kind: "retest", time: c[retestIdx].time, price: c[retestIdx].low, label: "Retest" },
    ],
    entryConditions: [
      `Daily close above ₹${formatPrice(entry)} (high of the post-retest swing).`,
      `Breakout zone ₹${formatPrice(zoneLow)}–${formatPrice(zoneHigh)} continues to hold on a closing basis.`,
      "Volume on the trigger session at or above the 20-day average.",
    ],
    invalidation: [
      `Daily close below ₹${formatPrice(stopLoss)} (below the retest low).`,
      `Close back inside the prior range, below ₹${formatPrice(zoneLow)}.`,
    ],
    evidence: [
      {
        title: "Multi-touch resistance was cleared",
        detail: `Price was rejected from ₹${formatPrice(zoneLow)}–${formatPrice(zoneHigh)} on three earlier occasions before closing above it on ${formatDate(c[boIdx].time)}.`,
        tone: "supporting",
      },
      {
        title: "Breakout came with participation",
        detail: `Breakout-day volume was ${volumeRatio.toFixed(1)}× the 20-day average, suggesting the move was not a low-liquidity drift.`,
        tone: volumeRatio >= 1.5 ? "supporting" : "caution",
      },
      {
        title: "Old resistance acted as support",
        detail: `The pullback to ₹${formatPrice(c[retestIdx].low)} held above the zone low, the classic role-reversal retest.`,
        tone: "supporting",
      },
      {
        title: "Overhead supply near the breakout high",
        detail: `Sellers previously appeared near ₹${formatPrice(c[peakIdx].high)}. Expect friction there before the projected target.`,
        tone: "caution",
      },
    ],
    volumeRatio,
  };
}

function buildBreakdown(g: GeneratedSeries): SetupBuild {
  const c = g.candles;
  const s = g.scale;
  const zoneLow = toTick(g.spec.refs.zoneLow * s);
  const zoneHigh = toTick(g.spec.refs.zoneHigh * s);
  const [bdA, bdB] = segRange(g, g.spec.marks.breakdown);
  const [rtA] = segRange(g, g.spec.marks.retest);
  const last = c.length - 1;

  let bdIdx = bdA;
  for (let i = bdA; i <= bdB; i++) if (c[i].close < zoneLow) { bdIdx = i; break; }
  const retestIdx = maxHigh(c, rtA, last);
  const triggerIdx = minLow(c, retestIdx, last - 1);
  const entry = toTick(c[triggerIdx].low * 0.999);
  const stopLoss = toTick(c[retestIdx].high * 1.006);
  const baseHigh = toTick(g.spec.refs.baseHigh * s);
  const target = toTick(zoneLow - (baseHigh - zoneLow) * 0.75);
  const volumeRatio = c[bdIdx].volume / avgVolume(c, bdIdx);

  return {
    type: "breakdown-retest",
    direction: "short",
    status: "detected",
    signal: "no-trade",
    headline: "Support failed and was retested from below. No long setup — structure is bearish.",
    levels: { entry, stopLoss, target, riskReward: rr(entry, stopLoss, target) },
    events: [
      { kind: "breakdown", time: c[bdIdx].time, price: c[bdIdx].close, label: "Breakdown" },
      { kind: "retest", time: c[retestIdx].time, price: c[retestIdx].high, label: "Retest" },
    ],
    entryConditions: [
      "Long entries are not considered while structure prints lower highs and lower lows.",
      `Short-side reference only: close below ₹${formatPrice(entry)}.`,
    ],
    invalidation: [
      `Bearish read is invalidated on a daily close above ₹${formatPrice(stopLoss)}.`,
      `Reclaiming ₹${formatPrice(zoneHigh)} would return price to the prior range.`,
    ],
    evidence: [
      {
        title: "Former support gave way",
        detail: `Price closed below the ₹${formatPrice(zoneLow)}–${formatPrice(zoneHigh)} zone on ${formatDate(c[bdIdx].time)} after multiple prior defences.`,
        tone: "caution",
      },
      {
        title: "Retest was rejected",
        detail: `The bounce to ₹${formatPrice(c[retestIdx].high)} stalled beneath the zone, confirming it as resistance.`,
        tone: "caution",
      },
      {
        title: "Breakdown volume",
        detail: `Breakdown-day volume was ${volumeRatio.toFixed(1)}× the 20-day average.`,
        tone: volumeRatio >= 1.5 ? "caution" : "supporting",
      },
    ],
    volumeRatio,
  };
}

function buildPullback(g: GeneratedSeries): SetupBuild {
  const c = g.candles;
  const s = g.scale;
  const zoneHigh = toTick(g.spec.refs.zoneHigh * s);
  const zoneLow = toTick(g.spec.refs.zoneLow * s);
  const [impA, impB] = segRange(g, g.spec.marks.impulse);
  const last = c.length - 1;
  const swingHighIdx = maxHigh(c, impA, impB);
  const recent = maxHigh(c, last - 2, last);
  const pullbackLow = c[minLow(c, impB, last)].low;
  const nearZone = c[last].close <= zoneHigh * 1.015;

  const entry = toTick(c[recent].high * 1.002);
  const stopLoss = toTick(Math.min(zoneLow, pullbackLow) * 0.992);
  const target = toTick(c[swingHighIdx].high + (c[swingHighIdx].high - g.spec.refs.lastHL * s) * 0.5);
  const volumeRatio = c[last].volume / avgVolume(c, last);

  return {
    type: "pullback-to-support",
    direction: "long",
    status: nearZone ? "awaiting-confirmation" : "detected",
    signal: "buy-watch",
    headline: nearZone
      ? "Uptrend pulling back into a prior breakout level on lighter volume."
      : "Uptrend pullback in progress; price has not yet reached the support zone.",
    levels: { entry, stopLoss, target, riskReward: rr(entry, stopLoss, target) },
    events: [],
    entryConditions: [
      `Price holds the ₹${formatPrice(zoneLow)}–${formatPrice(zoneHigh)} support zone.`,
      `Daily close above ₹${formatPrice(entry)} (high of the last three sessions).`,
      "Pullback volume remains below the advance's average.",
    ],
    invalidation: [
      `Daily close below ₹${formatPrice(stopLoss)}, under the support zone.`,
      "A lower low below the last higher low would break the uptrend.",
    ],
    evidence: [
      {
        title: "Trend structure intact",
        detail: "The sequence of higher highs and higher lows has not been violated.",
        tone: "supporting",
      },
      {
        title: "Pullback into role-reversal level",
        detail: `₹${formatPrice(zoneLow)}–${formatPrice(zoneHigh)} capped price earlier and is now being tested from above.`,
        tone: "supporting",
      },
      {
        title: "Selling pressure is light",
        detail: `Volume on the latest session is ${volumeRatio.toFixed(1)}× the 20-day average.`,
        tone: volumeRatio < 1 ? "supporting" : "caution",
      },
      {
        title: "No trigger yet",
        detail: "A pullback alone is not an entry. Wait for a bullish close above the trigger level.",
        tone: "caution",
      },
    ],
    volumeRatio,
  };
}

function buildRange(g: GeneratedSeries): SetupBuild {
  const c = g.candles;
  const s = g.scale;
  const resLow = toTick(g.spec.refs.resLow * s);
  const supHigh = toTick(g.spec.refs.supHigh * s);
  const supLow = toTick(g.spec.refs.supLow * s);
  const last = c.length - 1;
  const entry = toTick(supHigh * 1.004);
  const stopLoss = toTick(supLow * 0.99);
  const target = toTick(resLow);
  const posInRange = (c[last].close - supHigh) / (resLow - supHigh);

  return {
    type: "range-bound",
    direction: "long",
    status: "detected",
    signal: "no-trade",
    headline: `Price is ${posInRange > 0.35 && posInRange < 0.65 ? "in the middle" : posInRange >= 0.65 ? "in the upper half" : "in the lower half"} of an established range. No edge at current levels.`,
    levels: { entry, stopLoss, target, riskReward: rr(entry, stopLoss, target) },
    events: [],
    entryConditions: [
      `Reference only: a long is considered near range support (₹${formatPrice(supLow)}–${formatPrice(supHigh)}) with a bullish rejection.`,
      `Alternatively, a daily close above the range high ₹${formatPrice(resLow)} would create a range-breakout setup.`,
    ],
    invalidation: [`A daily close below ₹${formatPrice(stopLoss)} breaks the range to the downside.`],
    evidence: [
      {
        title: "Both boundaries tested repeatedly",
        detail: "Range high and low have each been respected four times, defining a clear trading range.",
        tone: "supporting",
      },
      {
        title: "Mid-range entries have poor risk/reward",
        detail: "Entering away from the boundaries places the stop far from entry and the target close.",
        tone: "caution",
      },
    ],
    volumeRatio: 1,
  };
}

const BUILDERS = {
  breakout: buildBreakout,
  breakdown: buildBreakdown,
  pullback: buildPullback,
  range: buildRange,
} as const;

function zonesFrom(g: GeneratedSeries): PriceZone[] {
  return g.spec.zones.map((z, i) => ({
    id: `z${i}`,
    kind: z.kind,
    low: toTick(z.low * g.scale),
    high: toTick(z.high * g.scale),
    label: z.label,
    touches: z.touches,
    strength: z.strength,
    fromTime: g.candles[g.segmentEnds[z.fromSeg]].time,
  }));
}

function trendSummary(structure: MarketStructure, swings: SwingPoint[]) {
  const recent = swings.slice(-4).map((s) => s.label).join(" → ");
  switch (structure) {
    case "uptrend":
      return `Higher highs and higher lows on the daily chart (${recent}).`;
    case "downtrend":
      return `Lower highs and lower lows on the daily chart (${recent}).`;
    case "transition":
      return `A change of character has occurred; the new trend is unconfirmed (${recent}).`;
    default:
      return `Mixed swing sequence with price rotating between boundaries (${recent}).`;
  }
}

function qualityFactors(structure: MarketStructure, build: SetupBuild, zones: PriceZone[], lastClose: number): QualityFactor[] {
  const aligned =
    (build.direction === "long" && structure === "uptrend") ||
    (build.direction === "short" && structure === "downtrend");
  const structureScore = aligned ? 88 : structure === "transition" ? 62 : structure === "range" ? 45 : 30;
  const maxTouches = Math.max(...zones.map((z) => z.touches));
  const zoneScore = clamp(40 + maxTouches * 12, 40, 92);
  const volScore = clamp(Math.round(build.volumeRatio * 42), 25, 95);
  const distance = Math.abs(build.levels.entry - lastClose) / lastClose;
  const proximityScore = clamp(Math.round(95 - distance * 1400), 20, 95);
  return [
    { label: "Structure alignment", score: structureScore, note: aligned ? "Setup direction matches trend" : "Setup not aligned with trend" },
    { label: "Level quality", score: zoneScore, note: `${maxTouches} touches on key zone` },
    { label: "Volume confirmation", score: volScore, note: `${build.volumeRatio.toFixed(1)}× average on key bar` },
    { label: "Risk / reward", score: scoreRR(build.levels.riskReward), note: `1 : ${build.levels.riskReward.toFixed(1)}` },
    { label: "Proximity to trigger", score: proximityScore, note: `${(distance * 100).toFixed(1)}% from entry` },
  ];
}

function biasFor(structure: MarketStructure, direction: "long" | "short", signal: SignalState): Bias {
  if (signal === "no-trade" && structure === "range") return "neutral";
  if (direction === "short") return "bearish";
  return structure === "downtrend" ? "bearish" : "bullish";
}

/* ---------- public API (consumed via the mock adapter only) ---------- */

const cache = new Map<string, StockAnalysis>();

/** Price and change at the snapshot: last closed 5m bar vs the previous session's close. */
function toStock(entry: UniverseEntry, previous: Candle, today: Candle[]): Stock {
  const last = today[today.length - 1];
  const change = Math.round((last.close - previous.close) * 100) / 100;
  return {
    symbol: entry.symbol,
    name: entry.name,
    exchange: entry.exchange,
    sector: entry.sector,
    indices: entry.indices,
    price: last.close,
    change,
    changePct: Math.round((change / previous.close) * 10000) / 100,
    volume: today.reduce((sum, b) => sum + b.volume, 0),
  };
}

export function buildDemoAnalysis(symbol: string): StockAnalysis | null {
  const key = symbol.toUpperCase();
  const cached = cache.get(key);
  if (cached) return cached;
  const entry = UNIVERSE.find((u) => u.symbol === key);
  if (!entry) return null;

  const g = generateSeries(entry);
  const pivots = zigzag(g.candles, ZIGZAG_THRESHOLD);
  const swings = labelSwings(g.candles, pivots).filter((s) => s.time >= g.candles[40].time);
  const breaks = detectBreaks(g.candles, pivots);
  const structure = entry.template === "range" ? "range" : classify(swings, breaks);
  const build = BUILDERS[entry.template](g);
  const zones = zonesFrom(g);
  // The snapshot session is still open at SAMPLE_AS_OF_TS: its daily bar is not complete, so it is left out of the
  // daily view, and nothing derived from it is shown (no look-ahead in sample data either).
  const closedDaily = g.candles.filter((c) => c.time < SAMPLE_AS_OF);
  const previous = closedDaily[closedDaily.length - 1];
  const intraday = intradayFor(entry.symbol, g.candles);
  const today = intraday["5m"].filter((b) => b.time.startsWith(SAMPLE_AS_OF));
  const session = sessionLevelsFor(previous, today);
  const stock = toStock(entry, previous, today);
  const factors = qualityFactors(structure, build, zones, stock.price);
  const qualityScore = Math.round(factors.reduce((a, f) => a + f.score, 0) / factors.length);

  const live = build.signal === "buy-watch" || build.signal === "entry-confirmed";
  const analysis: StockAnalysis = {
    stock,
    timeframe: "5m",
    asOf: SAMPLE_AS_OF_TS,
    candles: closedDaily,
    intraday,
    session,
    htfStructure: structure,
    signalAt: live ? SAMPLE_AS_OF_TS : null,
    // BUY WATCH lasts until the entry cutoff; ENTRY CONFIRMED only for the next 5m bar (TRD-04 §12).
    validUntil: build.signal === "buy-watch" ? session.entryCutoffAt : build.signal === "entry-confirmed" ? addMinutes(SAMPLE_AS_OF_TS, 5) : null,
    structure,
    bias: biasFor(structure, build.direction, build.signal),
    trendSummary: trendSummary(structure, swings),
    swings: swings.filter((x) => x.time < SAMPLE_AS_OF),
    breaks: breaks.filter((x) => x.toTime < SAMPLE_AS_OF),
    zones: zones.filter((x) => x.fromTime < SAMPLE_AS_OF),
    events: build.events.filter((x) => x.time < SAMPLE_AS_OF),
    setup: {
      type: build.type,
      direction: build.direction,
      status: build.status,
      signal: build.signal,
      headline: build.headline,
    },
    levels: build.levels,
    qualityScore,
    qualityFactors: factors,
    entryConditions: build.entryConditions,
    invalidation: build.invalidation,
    evidence: build.evidence,
  };
  cache.set(key, analysis);
  return analysis;
}

function addMinutes(iso: string, minutes: number) {
  const t = Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16)) + minutes;
  return `${iso.slice(0, 11)}${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}:00+05:30`;
}

export function allDemoSymbols() {
  return UNIVERSE.map((u) => u.symbol);
}
