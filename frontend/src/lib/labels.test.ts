import { describe, expect, it } from "vitest";
import { OUTCOMES, PLAN_STATUS, SETUP_STATUS, SETUP_TYPES, SIGNAL_STATES, STRUCTURES, TONE_CLASSES } from "./labels";

describe("labels", () => {
  it("never shows a bare BUY or SELL signal label", () => {
    for (const meta of Object.values(SIGNAL_STATES)) {
      expect(meta.label).not.toMatch(/^(BUY|SELL)$/);
      expect(meta.description.length).toBeGreaterThan(20);
    }
  });

  it("presents NO TRADE as a valid decision", () => {
    expect(SIGNAL_STATES["no-trade"].label).toBe("NO TRADE");
    expect(SIGNAL_STATES["no-trade"].description).toMatch(/valid decision/i);
  });

  it("makes clear BUY WATCH is not an entry", () => {
    expect(SIGNAL_STATES["buy-watch"].description).toMatch(/not an entry/i);
  });

  it("uses only defined tones", () => {
    const tones = new Set(Object.keys(TONE_CLASSES));
    const all = [SIGNAL_STATES, SETUP_STATUS, STRUCTURES, PLAN_STATUS, OUTCOMES].flatMap((m) => Object.values(m));
    for (const meta of all) expect(tones.has(meta.tone)).toBe(true);
  });

  it("has a label and short label for every setup type", () => {
    for (const meta of Object.values(SETUP_TYPES)) {
      expect(meta.label).toBeTruthy();
      expect(meta.short).toBeTruthy();
    }
  });
});
