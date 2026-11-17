/**
 * Time handling for the price chart (ARC-04 §2.9, PRD-07 §7 "Time axis").
 *
 * Lightweight Charts renders UTC. Intraday bars arrive as ISO timestamps with the IST offset; shifting them by
 * +05:30 before handing them to the chart makes its axis read in IST without a custom formatter. Daily bars keep
 * their session date ("YYYY-MM-DD"), which the library treats as a business day.
 */
import type { Time, UTCTimestamp } from "lightweight-charts";
import type { Candle } from "@/types";

const IST_OFFSET_SECONDS = 5.5 * 60 * 60;

export function isIntraday(time: string) {
  return time.length > 10;
}

/** Chart time for a bar start: business day for daily bars, IST-shifted UTC seconds for intraday bars. */
export function chartTime(time: string): Time {
  if (!isIntraday(time)) return time as Time;
  return (Math.floor(Date.parse(time) / 1000) + IST_OFFSET_SECONDS) as UTCTimestamp;
}

/** Session date (IST) of a bar start. */
export function sessionDate(time: string) {
  return time.slice(0, 10);
}

/** Bar starts that open a new session (the first bar of each session after the first), for separator lines. */
export function sessionStarts(candles: Candle[]): string[] {
  const out: string[] = [];
  for (let i = 1; i < candles.length; i++) {
    if (sessionDate(candles[i].time) !== sessionDate(candles[i - 1].time)) out.push(candles[i].time);
  }
  return out;
}
