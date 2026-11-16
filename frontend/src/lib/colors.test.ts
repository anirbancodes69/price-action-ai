import { describe, expect, it } from "vitest";
import { CHART_REST, CHART_SLOTS, TONE_BORDER, TONE_CHIP, TONE_FILL, TONE_TEXT, chartSlot, rrTone, scoreTone, signTone } from "./colors";
import { BIAS, OUTCOMES, PLAN_STATUS, SETUP_STATUS, SIGNAL_STATES, STRUCTURES } from "./labels";

describe("colors", () => {
  it("defines every tone in every form", () => {
    const tones = Object.keys(TONE_CHIP);
    for (const map of [TONE_TEXT, TONE_FILL, TONE_BORDER]) expect(Object.keys(map).sort()).toEqual([...tones].sort());
  });

  it("chips use the bg-{tone}/10 text-{tone} form (design-standards §6)", () => {
    for (const [tone, cls] of Object.entries(TONE_CHIP)) {
      if (tone === "neutral") continue;
      expect(cls).toBe(`bg-${tone}/10 text-${tone}`);
    }
  });

  it("never uses the brand accent for status or market tones", () => {
    const all = [TONE_CHIP, TONE_TEXT, TONE_FILL, TONE_BORDER].flatMap((m) => Object.values(m)).join(" ");
    expect(all).not.toMatch(/\b(primary|cta|chart-\d)/);
  });

  it("assigns chart slots in order and never cycles", () => {
    expect(CHART_SLOTS).toHaveLength(8);
    expect(chartSlot(0)).toBe("bg-chart-1");
    expect(chartSlot(7)).toBe("bg-chart-8");
    expect(chartSlot(8)).toBe(CHART_REST);
    expect(chartSlot(20)).toBe(CHART_REST);
  });

  it("bands quality scores and R:R", () => {
    expect(scoreTone(80)).toBe("success");
    expect(scoreTone(60)).toBe("warning");
    expect(scoreTone(40)).toBe("destructive");
    expect(rrTone(2.4)).toBe("success");
    expect(rrTone(1.6)).toBe("warning");
    expect(rrTone(1.2)).toBe("neutral");
  });

  it("maps a signed number to market direction", () => {
    expect(signTone(5)).toBe("bull");
    expect(signTone(-0.1)).toBe("bear");
    expect(signTone(0)).toBe("neutral");
  });

  it("keeps market direction for structure and bias, status tones for lifecycle states", () => {
    expect(STRUCTURES.uptrend.tone).toBe("bull");
    expect(STRUCTURES.downtrend.tone).toBe("bear");
    expect(BIAS.bullish.tone).toBe("bull");
    const statusOnly = [SIGNAL_STATES, SETUP_STATUS, PLAN_STATUS, OUTCOMES].flatMap((m) => Object.values(m));
    for (const meta of statusOnly) expect(["success", "warning", "destructive", "info", "neutral"]).toContain(meta.tone);
  });
});
