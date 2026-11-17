/**
 * SAMPLE DATA GENERATOR — intraday.
 *
 * Port of `backend/database/seeders/Demo/DemoIntradayGenerator.php` (ADR-015, ENG-05 §12 "Demo data"), so the UI's
 * sample 5m/15m bars equal the seeded DEMO bars. Each session's 5m bars agree with that session's daily bar: first
 * open = daily open, last close = daily close, session high/low = daily high/low, volumes sum to the daily volume.
 * 15m bars are aggregated from the 5m bars. The order of every random draw matches the PHP source; a parity test
 * compares against a fixture exported from it. Never market data.
 */
import type { Candle } from "@/types";
import { hashString, mulberry32 } from "./rng";

export const BARS_5M = 75;
const SESSION_OPEN_MINUTES = 9 * 60 + 15;

/** PHP DemoRandom::toTick: floor(n·20 + 0.5)/20 (ties toward +∞, as JavaScript Math.round). */
const toTick = (n: number) => Math.floor(n * 20 + 0.5) / 20;

/** ISO-8601 with the IST offset for a session date and minutes after midnight, e.g. 2026-11-13T09:15:00+05:30. */
export function istTimestamp(date: string, minutes: number) {
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  return `${date}T${hh}:${mm}:00+05:30`;
}

/** 5-minute bars for one session, consistent with the daily bar (`time` of the daily bar is its session date). */
export function fiveMinuteBars(symbol: string, daily: Candle): Candle[] {
  const rnd = mulberry32(hashString(`${symbol}@${daily.time}`));
  const { open: o, high: h, low: l, close: c } = daily;
  const n = BARS_5M;
  const amp = Math.max(h - l, 0.05) / 3;

  const walk = [0];
  for (let k = 1; k <= n; k++) walk[k] = walk[k - 1] + (rnd() - 0.5);
  let scale = 0;
  const bridge: number[] = [];
  for (let k = 0; k <= n; k++) {
    bridge[k] = walk[k] - (k / n) * walk[n];
    scale = Math.max(scale, Math.abs(bridge[k]));
  }
  scale = scale > 0 ? scale : 1;

  const path: number[] = [];
  for (let k = 0; k <= n; k++) {
    const base = o + ((c - o) * k) / n;
    path[k] = Math.min(h, Math.max(l, base + (amp * bridge[k]) / scale));
  }
  path[0] = o;
  path[n] = c;

  const weights: number[] = [];
  for (let k = 1; k <= n; k++) {
    const x = (k - (n + 1) / 2) / ((n - 1) / 2);
    weights[k] = (1 + 1.5 * x * x) * (0.7 + 0.6 * rnd());
  }
  let weightSum = 0;
  for (let k = 1; k <= n; k++) weightSum += weights[k];

  const bars: Candle[] = [];
  let volumeLeft = daily.volume;
  for (let k = 1; k <= n; k++) {
    const open = toTick(path[k - 1]);
    const close = toTick(path[k]);
    const wick = amp * 0.15;
    const high = Math.min(h, toTick(Math.max(open, close) + wick * rnd()));
    const low = Math.max(l, toTick(Math.min(open, close) - wick * rnd()));
    const volume = k === n ? volumeLeft : Math.floor((daily.volume * weights[k]) / weightSum);
    volumeLeft -= volume;
    bars.push({
      time: istTimestamp(daily.time, SESSION_OPEN_MINUTES + 5 * (k - 1)),
      open,
      high: Math.max(high, open, close),
      low: Math.min(low, open, close),
      close,
      volume,
    });
  }
  bars[0].open = o;
  bars[n - 1].close = c;

  let hi = 0;
  let lo = 0;
  bars.forEach((b, i) => {
    if (b.high > bars[hi].high) hi = i;
    if (b.low < bars[lo].low) lo = i;
  });
  bars[hi].high = h;
  bars[lo].low = l;
  for (const b of bars) {
    b.high = Math.max(b.high, b.open, b.close);
    b.low = Math.min(b.low, b.open, b.close);
  }
  return bars;
}

/** Aggregate consecutive groups of three 5m bars into 15m bars (display and consistency only). */
export function fifteenMinuteBars(bars: Candle[]): Candle[] {
  const out: Candle[] = [];
  for (let i = 0; i < bars.length; i += 3) {
    const g = bars.slice(i, i + 3);
    out.push({
      time: g[0].time,
      open: g[0].open,
      high: Math.max(...g.map((b) => b.high)),
      low: Math.min(...g.map((b) => b.low)),
      close: g[g.length - 1].close,
      volume: g.reduce((s, b) => s + b.volume, 0),
    });
  }
  return out;
}
