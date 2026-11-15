/** SAMPLE DATA — representative index values for the demo. Not live. */
import type { MarketIndex } from "@/types";
import { mulberry32 } from "./rng";

function trend(seed: number, end: number, drift: number, n = 30) {
  const rnd = mulberry32(seed);
  const out: number[] = [];
  let v = end / (1 + drift);
  for (let i = 0; i < n; i++) {
    v *= 1 + drift / n + (rnd() - 0.5) * 0.008;
    out.push(Math.round(v * 100) / 100);
  }
  out[n - 1] = end;
  return out;
}

export const INDICES: MarketIndex[] = [
  { id: "nifty50", name: "NIFTY 50", value: 26_142.35, change: 118.4, changePct: 0.45, trend: trend(11, 26_142.35, 0.032) },
  { id: "niftybank", name: "NIFTY BANK", value: 59_318.6, change: 287.15, changePct: 0.49, trend: trend(23, 59_318.6, 0.041) },
  { id: "sensex", name: "SENSEX", value: 85_486.2, change: 341.9, changePct: 0.4, trend: trend(37, 85_486.2, 0.029) },
  { id: "indiavix", name: "INDIA VIX", value: 12.84, change: -0.42, changePct: -3.17, trend: trend(41, 12.84, -0.09) },
];
