"use client";

import { useSyncExternalStore } from "react";

/**
 * Intraday session phases (TRD-01 §4.1, PRD-07 UX-09). Normal NSE session only: entry cutoff 14:45 (45 min before
 * the close), session-end exit 15:15 (15 min before the close). Holidays and special sessions need the calendar API.
 */
export type SessionPhase = "pre-open" | "open" | "after-cutoff" | "exit-window" | "closed";

export interface SessionClock {
  phase: SessionPhase;
  /** The next session event and the minutes until it, or null when the market is closed. */
  next: { label: "Open" | "Entry cutoff" | "Session-end exit" | "Close"; minutes: number } | null;
}

const OPEN = 9 * 60 + 15;
const CUTOFF = 14 * 60 + 45;
const EXIT = 15 * 60 + 15;
const CLOSE = 15 * 60 + 30;

export function sessionClock(date: Date): SessionClock {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  const weekday = get("weekday");
  if (weekday === "Sat" || weekday === "Sun") return { phase: "closed", next: null };
  const m = Number(get("hour")) * 60 + Number(get("minute"));
  if (m >= 9 * 60 && m < OPEN) return { phase: "pre-open", next: { label: "Open", minutes: OPEN - m } };
  if (m >= OPEN && m < CUTOFF) return { phase: "open", next: { label: "Entry cutoff", minutes: CUTOFF - m } };
  if (m >= CUTOFF && m < EXIT) return { phase: "after-cutoff", next: { label: "Session-end exit", minutes: EXIT - m } };
  if (m >= EXIT && m < CLOSE) return { phase: "exit-window", next: { label: "Close", minutes: CLOSE - m } };
  return { phase: "closed", next: null };
}

/** "1h 05m" / "12m". */
export function formatCountdown(minutes: number) {
  const h = Math.floor(minutes / 60);
  const mm = minutes % 60;
  return h > 0 ? `${h}h ${String(mm).padStart(2, "0")}m` : `${mm}m`;
}

let clockKey: string | null = null;
let clockValue: SessionClock | null = null;
const clockListeners = new Set<() => void>();
let clockInterval: ReturnType<typeof setInterval> | null = null;

function readClock(): SessionClock {
  const c = sessionClock(new Date());
  const key = `${c.phase}|${c.next?.minutes ?? ""}`;
  if (key !== clockKey) {
    clockKey = key;
    clockValue = c;
  }
  return clockValue as SessionClock;
}

function subscribeClock(cb: () => void) {
  clockListeners.add(cb);
  if (!clockInterval) clockInterval = setInterval(() => clockListeners.forEach((l) => l()), 20_000);
  return () => {
    clockListeners.delete(cb);
    if (clockListeners.size === 0 && clockInterval) {
      clearInterval(clockInterval);
      clockInterval = null;
    }
  };
}

/** Session phase and countdown; null during SSR / before hydration. */
export function useSessionClock(): SessionClock | null {
  return useSyncExternalStore(subscribeClock, readClock, () => null);
}
