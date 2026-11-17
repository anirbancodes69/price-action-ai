/**
 * SAMPLE DATA — intraday series and session levels for the demo snapshot (ADR-014/015).
 *
 * Builds the last sessions' 5m and 15m bars from the daily series (demo-intraday.ts) and cuts the snapshot session at
 * SAMPLE_SNAPSHOT, keeping only bars that have closed by then. Session levels follow TRD-03 §8 and session times
 * TRD-01 §4.1 (normal session; holidays are not modelled in sample data).
 */
import type { Candle, SessionLevels } from "@/types";
import { fifteenMinuteBars, fiveMinuteBars, istTimestamp } from "./demo-intraday";
import { SAMPLE_AS_OF, SAMPLE_SNAPSHOT } from "./universe";

export const INTRADAY_SESSIONS = 10;
const OPENING_RANGE_BARS = 3; // 15 minutes of 5m bars (session.opening_range_minutes)
const ENTRY_CUTOFF = 14 * 60 + 45; // 45 min before the 15:30 close
const SESSION_END_EXIT = 15 * 60 + 15; // 15 min before the close

const minutesOf = (iso: string) => Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16));
const snapshotMinutes = minutesOf(`0000-00-00T${SAMPLE_SNAPSHOT}`);

/** Only bars whose end (start + interval) is at or before the snapshot are kept for the snapshot session. */
function closedBy(bars: Candle[], intervalMinutes: number) {
  return bars.filter((b) => !b.time.startsWith(SAMPLE_AS_OF) || minutesOf(b.time) + intervalMinutes <= snapshotMinutes);
}

export function intradayFor(symbol: string, daily: Candle[]): { "5m": Candle[]; "15m": Candle[] } {
  const sessions = daily.slice(-INTRADAY_SESSIONS);
  const five: Candle[] = [];
  const fifteen: Candle[] = [];
  for (const d of sessions) {
    const bars = fiveMinuteBars(symbol, d);
    five.push(...bars);
    fifteen.push(...fifteenMinuteBars(bars));
  }
  return { "5m": closedBy(five, 5), "15m": closedBy(fifteen, 15) };
}

/** `previous` is the last completed session's daily bar; `today` the snapshot session's closed 5m bars. */
export function sessionLevelsFor(previous: Candle, today: Candle[]): SessionLevels {
  const or = today.length >= OPENING_RANGE_BARS ? today.slice(0, OPENING_RANGE_BARS) : null;
  return {
    pdh: previous.high,
    pdl: previous.low,
    pdc: previous.close,
    orHigh: or ? Math.max(...or.map((b) => b.high)) : null,
    orLow: or ? Math.min(...or.map((b) => b.low)) : null,
    sessionHigh: Math.max(...today.map((b) => b.high)),
    sessionLow: Math.min(...today.map((b) => b.low)),
    entryCutoffAt: istTimestamp(SAMPLE_AS_OF, ENTRY_CUTOFF),
    sessionEndExitAt: istTimestamp(SAMPLE_AS_OF, SESSION_END_EXIT),
  };
}
