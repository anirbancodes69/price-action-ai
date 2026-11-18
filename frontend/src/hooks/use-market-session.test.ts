import { describe, expect, it } from "vitest";
import { formatCountdown, sessionClock } from "./use-market-session";

// 2026-11-13 is a Friday; times are IST.
const at = (hhmm: string, date = "2026-11-13") => new Date(`${date}T${hhmm}:00+05:30`);

describe("session clock (TRD-01 §4.1)", () => {
  it("walks through the intraday phases", () => {
    expect(sessionClock(at("08:59"))).toEqual({ phase: "closed", next: null });
    expect(sessionClock(at("09:05"))).toEqual({ phase: "pre-open", next: { label: "Open", minutes: 10 } });
    expect(sessionClock(at("09:15"))).toEqual({ phase: "open", next: { label: "Entry cutoff", minutes: 330 } });
    expect(sessionClock(at("14:44"))).toEqual({ phase: "open", next: { label: "Entry cutoff", minutes: 1 } });
    expect(sessionClock(at("14:45"))).toEqual({ phase: "after-cutoff", next: { label: "Session-end exit", minutes: 30 } });
    expect(sessionClock(at("15:15"))).toEqual({ phase: "exit-window", next: { label: "Close", minutes: 15 } });
    expect(sessionClock(at("15:30"))).toEqual({ phase: "closed", next: null });
  });

  it("is closed at weekends", () => {
    expect(sessionClock(at("11:00", "2026-11-14")).phase).toBe("closed");
  });

  it("formats countdowns", () => {
    expect(formatCountdown(65)).toBe("1h 05m");
    expect(formatCountdown(12)).toBe("12m");
  });
});
