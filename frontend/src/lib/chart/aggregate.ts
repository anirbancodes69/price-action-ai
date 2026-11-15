import type { Candle, Timeframe } from "@/types";

/** Monday of the ISO week for a YYYY-MM-DD day. */
function weekKey(day: string) {
  const d = new Date(`${day}T00:00:00Z`);
  const dow = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dow);
  return d.toISOString().slice(0, 10);
}

function monthKey(day: string) {
  return `${day.slice(0, 7)}-01`;
}

export function bucketFor(tf: Timeframe): (day: string) => string {
  if (tf === "1W") return weekKey;
  if (tf === "1M") return monthKey;
  return (d) => d;
}

/** Aggregates daily candles to weekly/monthly bars. */
export function aggregate(candles: Candle[], tf: Timeframe): Candle[] {
  if (tf === "1D") return candles;
  const key = bucketFor(tf);
  const out: Candle[] = [];
  for (const c of candles) {
    const k = key(c.time);
    const last = out[out.length - 1];
    if (last && last.time === k) {
      last.high = Math.max(last.high, c.high);
      last.low = Math.min(last.low, c.low);
      last.close = c.close;
      last.volume += c.volume;
    } else {
      out.push({ ...c, time: k });
    }
  }
  return out;
}
