"use client";

import { useSyncExternalStore } from "react";
import type { MarketSession } from "@/types";

/**
 * NSE equity session derived from the clock in IST (pre-open 09:00–09:15,
 * normal 09:15–15:30, Mon–Fri). Exchange holidays are NOT considered yet;
 * a market-calendar API should replace this in a later phase.
 */
export function sessionAt(date: Date): MarketSession {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(date);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  const weekday = get("weekday");
  if (weekday === "Sat" || weekday === "Sun") return "closed";
  const mins = Number(get("hour")) * 60 + Number(get("minute"));
  if (mins >= 9 * 60 && mins < 9 * 60 + 15) return "pre-open";
  if (mins >= 9 * 60 + 15 && mins < 15 * 60 + 30) return "open";
  return "closed";
}

let current: MarketSession | null = null;
const listeners = new Set<() => void>();
let interval: ReturnType<typeof setInterval> | null = null;

function subscribe(cb: () => void) {
  listeners.add(cb);
  if (!interval) {
    current = sessionAt(new Date());
    interval = setInterval(() => {
      const next = sessionAt(new Date());
      if (next !== current) {
        current = next;
        listeners.forEach((l) => l());
      }
    }, 30_000);
  }
  return () => {
    listeners.delete(cb);
    if (listeners.size === 0 && interval) {
      clearInterval(interval);
      interval = null;
    }
  };
}

/** Returns null during SSR / before hydration to avoid mismatches. */
export function useMarketSession(): MarketSession | null {
  return useSyncExternalStore(
    subscribe,
    () => current ?? (current = sessionAt(new Date())),
    () => null,
  );
}
