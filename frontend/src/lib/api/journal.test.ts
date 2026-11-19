import { describe, expect, it } from "vitest";
import { mapJournalEntry, type ApiJournalEntry } from "./journal";

const api: ApiJournalEntry = {
  id: "j1",
  kind: "ACTUAL",
  status: "DRAFT",
  trade: {
    symbol: "RELIANCE", setup_type: null, direction: "LONG", entry_at: "2026-11-18T10:00:00+05:30", exit_at: "2026-11-18T11:00:00+05:30",
    entry_price: "100.00", exit_price: "110.00", quantity: 10, net_pnl: "91.00", r_multiple: null, outcome: "WIN",
  },
  followed_plan: null,
  notes: null,
  tags: ["orb"],
};

describe("mapJournalEntry", () => {
  it("converts the vocabulary and decimals, keeping unknowns null", () => {
    expect(mapJournalEntry(api)).toEqual({
      id: "j1", symbol: "RELIANCE", setupType: null, direction: "long", entryDate: "2026-11-18T10:00:00+05:30",
      exitDate: "2026-11-18T11:00:00+05:30", entryPrice: 100, exitPrice: 110, quantity: 10, pnl: 91, rMultiple: null,
      outcome: "win", followedPlan: null, notes: "", tags: ["orb"],
    });
  });

  it("maps a plan-linked trade: setup type, R multiple, loss, followed", () => {
    const e = mapJournalEntry({
      ...api,
      trade: { ...api.trade, setup_type: "OPENING_RANGE_BREAKOUT", r_multiple: "-1.5", net_pnl: "-59.00", outcome: "LOSS" },
      followed_plan: true,
      notes: "Too early",
    });
    expect([e.setupType, e.rMultiple, e.pnl, e.outcome, e.followedPlan, e.notes]).toEqual(["opening-range-breakout", -1.5, -59, "loss", true, "Too early"]);
  });
});
